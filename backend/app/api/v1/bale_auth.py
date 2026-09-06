import re
import secrets
from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.bale_auth import CustomerAccount
from app.schemas.bale_auth import (
    BaleChallengeCreate,
    BaleChallengeCreated,
    BaleChallengeExchange,
    BaleChallengeRead,
    CustomerRead,
)
from app.services.bale_auth import (
    BaleBotGateway,
    BaleChallengeUnavailable,
    BaleIdentity,
    BaleLoginNotConfigured,
    approve_challenge,
    as_utc,
    create_challenge,
    exchange_challenge,
    find_challenge_by_code,
    get_challenge,
    utc_now,
)

router = APIRouter()
customer_bearer = HTTPBearer(auto_error=False)
CODE_PATTERN = re.compile(r"(?:^/start\s+)?(?P<code>\d{6})$")
CALLBACK_PREFIX = "bale_login_confirm:"


def remaining_seconds(expires_at) -> int:
    normalized = expires_at
    if normalized.tzinfo is None:
        normalized = normalized.replace(tzinfo=timezone.utc)
    return max(0, int((normalized - utc_now()).total_seconds()))


@router.post("/challenges", response_model=BaleChallengeCreated, status_code=status.HTTP_201_CREATED)
def start_bale_login(payload: BaleChallengeCreate, db: Session = Depends(get_db)) -> BaleChallengeCreated:
    try:
        challenge, code, bot_url = create_challenge(db, return_path=payload.return_path)
    except BaleLoginNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return BaleChallengeCreated(
        id=challenge.id,
        code=code,
        status="pending",
        expires_at_utc=as_utc(challenge.expires_at_utc),
        expires_in_seconds=int(
            (challenge.expires_at_utc - challenge.created_at_utc).total_seconds()
        ),
        bot_url=bot_url,
    )


@router.get("/challenges/{challenge_id}", response_model=BaleChallengeRead)
def read_bale_login(challenge_id: str, db: Session = Depends(get_db)) -> BaleChallengeRead:
    challenge = get_challenge(db, challenge_id)
    if not challenge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="درخواست ورود پیدا نشد.")
    return BaleChallengeRead(
        id=challenge.id,
        status=challenge.status,
        expires_at_utc=as_utc(challenge.expires_at_utc),
        expires_in_seconds=remaining_seconds(challenge.expires_at_utc),
    )


@router.post("/challenges/{challenge_id}/exchange", response_model=BaleChallengeExchange)
def exchange_bale_login(challenge_id: str, db: Session = Depends(get_db)) -> BaleChallengeExchange:
    try:
        challenge, customer = exchange_challenge(db, challenge_id=challenge_id)
    except BaleChallengeUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    token = create_access_token(
        f"customer:{customer.id}", claims={"actor_type": "customer", "provider": "bale"}
    )
    return BaleChallengeExchange(
        access_token=token,
        return_path=challenge.return_path,
        customer=CustomerRead(id=customer.id, display_name=customer.display_name),
    )


@router.get("/me", response_model=CustomerRead)
def read_bale_customer(
    credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer),
    db: Session = Depends(get_db),
) -> CustomerRead:
    auth_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="نشست مشتری معتبر نیست. دوباره با بله وارد شوید.",
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise auth_error
    try:
        payload = decode_access_token(credentials.credentials)
        subject = str(payload.get("sub") or "")
        if payload.get("actor_type") != "customer" or not subject.startswith("customer:"):
            raise auth_error
        customer_id = int(subject.removeprefix("customer:"))
    except (JWTError, TypeError, ValueError) as exc:
        raise auth_error from exc
    customer = db.get(CustomerAccount, customer_id)
    if not customer or not customer.is_active:
        raise auth_error
    return CustomerRead(id=customer.id, display_name=customer.display_name)


def identity_from_update(source: dict, chat_id: object) -> BaleIdentity | None:
    user_id = source.get("id")
    if user_id is None or chat_id is None:
        return None
    name = " ".join(
        part.strip() for part in (source.get("first_name", ""), source.get("last_name", "")) if part and part.strip()
    )
    return BaleIdentity(
        user_id=str(user_id),
        display_name=name or source.get("username"),
        username=source.get("username"),
        chat_id=str(chat_id),
    )


@router.post("/webhook/{webhook_secret}", include_in_schema=False)
def bale_webhook(webhook_secret: str, update_payload: dict, db: Session = Depends(get_db)) -> dict[str, bool]:
    configured_secret = get_settings().bale_webhook_secret
    if not configured_secret or not secrets.compare_digest(webhook_secret, configured_secret):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    try:
        gateway = BaleBotGateway()
    except BaleLoginNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    callback = update_payload.get("callback_query") or {}
    callback_data = callback.get("data", "")
    if callback_data.startswith(CALLBACK_PREFIX):
        code = callback_data.removeprefix(CALLBACK_PREFIX)
        message = callback.get("message") or {}
        identity = identity_from_update(callback.get("from") or {}, (message.get("chat") or {}).get("id"))
        challenge = (
            approve_challenge(db, code=code, identity=identity)
            if identity and re.fullmatch(r"\d{6}", code)
            else None
        )
        callback_id = callback.get("id")
        if callback_id:
            gateway.answer_callback(
                callback_id=str(callback_id),
                text="ورود تأیید شد." if challenge else "کد منقضی یا نامعتبر است.",
            )
        if challenge and identity:
            gateway.send_result(chat_id=identity.chat_id, challenge_id=challenge.id)
        elif identity:
            gateway.send_expired(chat_id=identity.chat_id)
        return {"ok": True}

    message = update_payload.get("message") or {}
    text = str(message.get("text") or "").strip()
    match = CODE_PATTERN.fullmatch(text)
    identity = identity_from_update(message.get("from") or {}, (message.get("chat") or {}).get("id"))
    if identity and match:
        code = match.group("code")
        if find_challenge_by_code(db, code):
            gateway.send_confirmation(chat_id=identity.chat_id, code=code)
        else:
            gateway.send_expired(chat_id=identity.chat_id)
    elif identity:
        gateway.call(
            "sendMessage",
            {"chat_id": identity.chat_id, "text": "برای ورود، کد شش‌رقمی نمایش‌داده‌شده در فروشگاه را ارسال کنید."},
        )
    return {"ok": True}
