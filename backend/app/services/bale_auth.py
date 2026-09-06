from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib import error, request
from uuid import uuid4

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.bale_auth import BaleLoginChallenge, CustomerAccount

logger = logging.getLogger(__name__)


class BaleLoginError(Exception):
    pass


class BaleLoginNotConfigured(BaleLoginError):
    pass


class BaleChallengeUnavailable(BaleLoginError):
    pass


@dataclass(frozen=True)
class BaleIdentity:
    user_id: str
    display_name: str | None
    username: str | None
    chat_id: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def hash_login_code(code: str) -> str:
    secret = get_settings().secret_key.encode("utf-8")
    return hmac.new(secret, code.encode("ascii"), hashlib.sha256).hexdigest()


def require_bale_configuration() -> tuple[str, str]:
    settings = get_settings()
    username = settings.bale_bot_username.strip().lstrip("@")
    if not settings.bale_bot_token.strip() or not username or not settings.bale_webhook_secret.strip():
        raise BaleLoginNotConfigured("ورود با بله هنوز روی سرور پیکربندی نشده است.")
    return username, settings.bale_bot_token.strip()


def create_challenge(db: Session, *, return_path: str) -> tuple[BaleLoginChallenge, str, str]:
    username, _ = require_bale_configuration()
    settings = get_settings()
    now = utc_now()
    ttl_seconds = settings.bale_login_ttl_seconds

    for _ in range(20):
        code = f"{secrets.randbelow(1_000_000):06d}"
        code_hash = hash_login_code(code)
        collision = (
            db.query(BaleLoginChallenge)
            .filter(
                BaleLoginChallenge.code_hash == code_hash,
                BaleLoginChallenge.status.in_(("pending", "approved")),
                BaleLoginChallenge.expires_at_utc > now,
            )
            .first()
        )
        if not collision:
            break
    else:
        raise BaleChallengeUnavailable("ساخت کد ورود ممکن نشد؛ دوباره تلاش کنید.")

    challenge = BaleLoginChallenge(
        id=str(uuid4()),
        code_hash=code_hash,
        status="pending",
        return_path=return_path,
        created_at_utc=now,
        expires_at_utc=now + timedelta(seconds=ttl_seconds),
    )
    db.add(challenge)
    db.commit()
    db.refresh(challenge)
    return challenge, code, f"https://ble.ir/{username}?start={code}"


def refresh_expiry(db: Session, challenge: BaleLoginChallenge) -> BaleLoginChallenge:
    if challenge.status in ("pending", "approved") and as_utc(challenge.expires_at_utc) <= utc_now():
        challenge.status = "expired"
        db.commit()
        db.refresh(challenge)
    return challenge


def get_challenge(db: Session, challenge_id: str) -> BaleLoginChallenge | None:
    challenge = db.get(BaleLoginChallenge, challenge_id)
    return refresh_expiry(db, challenge) if challenge else None


def find_challenge_by_code(db: Session, code: str) -> BaleLoginChallenge | None:
    now = utc_now()
    challenge = (
        db.query(BaleLoginChallenge)
        .filter(
            BaleLoginChallenge.code_hash == hash_login_code(code),
            BaleLoginChallenge.status.in_(("pending", "approved")),
            BaleLoginChallenge.expires_at_utc > now,
        )
        .order_by(BaleLoginChallenge.created_at_utc.desc())
        .first()
    )
    return challenge


def approve_challenge(db: Session, *, code: str, identity: BaleIdentity) -> BaleLoginChallenge | None:
    challenge = find_challenge_by_code(db, code)
    if not challenge:
        return None
    if challenge.status == "approved":
        return challenge if challenge.bale_user_id == identity.user_id else None

    approved_at = utc_now()
    result = db.execute(
        update(BaleLoginChallenge)
        .where(
            BaleLoginChallenge.id == challenge.id,
            BaleLoginChallenge.status == "pending",
            BaleLoginChallenge.expires_at_utc > approved_at,
        )
        .values(
            status="approved",
            bale_user_id=identity.user_id,
            bale_display_name=identity.display_name,
            bale_username=identity.username,
            approved_at_utc=approved_at,
        )
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        db.rollback()
        current = db.get(BaleLoginChallenge, challenge.id)
        if current and current.status == "approved" and current.bale_user_id == identity.user_id:
            return current
        return None

    db.commit()
    db.refresh(challenge)
    return challenge


def exchange_challenge(db: Session, *, challenge_id: str) -> tuple[BaleLoginChallenge, CustomerAccount]:
    challenge = db.get(BaleLoginChallenge, challenge_id)
    if not challenge:
        raise BaleChallengeUnavailable("درخواست ورود پیدا نشد.")
    challenge = refresh_expiry(db, challenge)
    if challenge.status != "approved" or not challenge.bale_user_id:
        raise BaleChallengeUnavailable(
            "این درخواست هنوز تأیید نشده، منقضی شده یا قبلاً استفاده شده است."
        )

    now = utc_now()
    result = db.execute(
        update(BaleLoginChallenge)
        .where(
            BaleLoginChallenge.id == challenge.id,
            BaleLoginChallenge.status == "approved",
            BaleLoginChallenge.consumed_at_utc.is_(None),
            BaleLoginChallenge.expires_at_utc > now,
        )
        .values(status="consumed", consumed_at_utc=now)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        db.rollback()
        raise BaleChallengeUnavailable("این درخواست ورود قبلاً استفاده شده یا منقضی شده است.")

    customer = (
        db.query(CustomerAccount)
        .filter(
            CustomerAccount.provider == "bale",
            CustomerAccount.provider_user_id == challenge.bale_user_id,
        )
        .first()
    )
    if customer is None:
        customer = CustomerAccount(
            provider="bale",
            provider_user_id=challenge.bale_user_id,
            display_name=challenge.bale_display_name,
            provider_username=challenge.bale_username,
            last_login_at_utc=now,
        )
        db.add(customer)
        db.flush()
    else:
        if not customer.is_active:
            db.rollback()
            raise BaleChallengeUnavailable("این حساب مشتری غیرفعال است.")
        customer.display_name = challenge.bale_display_name or customer.display_name
        customer.provider_username = challenge.bale_username or customer.provider_username
        customer.last_login_at_utc = now

    challenge.customer_account_id = customer.id
    db.commit()
    db.refresh(challenge)
    db.refresh(customer)
    return challenge, customer


class BaleBotGateway:
    def __init__(self) -> None:
        _, token = require_bale_configuration()
        self.base_url = f"https://tapi.bale.ai/bot{token}"

    def call(self, method: str, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/{method}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=8) as response:
                response.read()
        except (error.URLError, TimeoutError, OSError) as exc:
            logger.warning("Bale Bot API request failed for %s: %s", method, type(exc).__name__)

    def send_confirmation(self, *, chat_id: str, code: str) -> None:
        self.call(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": "برای ورود به فروشگاه، دکمه زیر را بزنید. این درخواست فقط دو دقیقه معتبر است.",
                "reply_markup": {
                    "inline_keyboard": [[
                        {"text": "تأیید ورود", "callback_data": f"bale_login_confirm:{code}"}
                    ]]
                },
            },
        )

    def send_result(self, *, chat_id: str, challenge_id: str) -> None:
        base_url = get_settings().public_base_url.rstrip("/")
        return_url = f"{base_url}/?bale_login={challenge_id}"
        self.call(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": "ورود شما تأیید شد. اگر با موبایل وارد شده‌اید، به فروشگاه برگردید.",
                "reply_markup": {
                    "inline_keyboard": [[{"text": "بازگشت به فروشگاه", "url": return_url}]]
                },
            },
        )

    def send_expired(self, *, chat_id: str) -> None:
        self.call(
            "sendMessage",
            {"chat_id": chat_id, "text": "این کد معتبر نیست یا زمان دو دقیقه‌ای آن تمام شده است. از فروشگاه کد تازه بگیرید."},
        )

    def answer_callback(self, *, callback_id: str, text: str) -> None:
        self.call("answerCallbackQuery", {"callback_query_id": callback_id, "text": text})
