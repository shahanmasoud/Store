"""Configure the Bale Bot webhook without printing secrets."""

from __future__ import annotations

import json
from urllib import error, request

from app.core.config import get_settings


def call_bale(method: str, payload: dict | None = None) -> dict:
    settings = get_settings()
    token = settings.bale_bot_token.strip()
    if not token:
        raise RuntimeError("BALE_BOT_TOKEN is not configured")
    body = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        f"https://tapi.bale.ai/bot{token}/{method}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        raise RuntimeError(f"Bale API returned HTTP {exc.code}") from exc
    except (error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Could not reach Bale API: {type(exc).__name__}") from exc
    if not result.get("ok"):
        raise RuntimeError("Bale API rejected the request")
    return result


def main() -> None:
    settings = get_settings()
    username = settings.bale_bot_username.strip().lstrip("@")
    secret = settings.bale_webhook_secret.strip()
    base_url = settings.public_base_url.rstrip("/")
    if not username or not secret or not base_url.startswith("https://"):
        raise RuntimeError(
            "BALE_BOT_USERNAME, BALE_WEBHOOK_SECRET and an HTTPS PUBLIC_BASE_URL are required"
        )

    bot_info = call_bale("getMe").get("result") or {}
    actual_username = str(bot_info.get("username") or "").lstrip("@")
    if actual_username and actual_username.casefold() != username.casefold():
        raise RuntimeError("BALE_BOT_USERNAME does not match the supplied bot token")

    if settings.bale_polling_fallback:
        call_bale("setWebhook", {"url": ""})
        print(f"Bale polling fallback configured for @{username}")
        return

    webhook_url = f"{base_url}/api/v1/auth/bale/webhook/{secret}"
    call_bale("setWebhook", {"url": webhook_url})
    print(f"Bale webhook configured for @{username} on {base_url}")


if __name__ == "__main__":
    main()
