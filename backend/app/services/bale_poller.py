from __future__ import annotations

import json
import logging
from threading import Event, Lock, Thread
from urllib import error, request

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.bale_auth import get_bale_credentials

logger = logging.getLogger(__name__)


class BalePollingWorker:
    def __init__(self) -> None:
        self.stop_event = Event()
        self.thread: Thread | None = None
        self.offset: int | None = None

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = Thread(target=self.run, name="bale-login-poller", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3)

    def run(self) -> None:
        logger.info("Bale polling fallback started")
        while not self.stop_event.is_set():
            try:
                updates = self.fetch_updates()
                for update_payload in updates:
                    if not self.deliver_update(update_payload):
                        break
                    update_id = update_payload.get("update_id")
                    if isinstance(update_id, int):
                        self.offset = update_id + 1
                if not updates:
                    self.stop_event.wait(2)
            except Exception as exc:  # worker must survive transient provider/network failures
                logger.warning("Bale polling cycle failed: %s", type(exc).__name__)
                self.stop_event.wait(3)

    def fetch_updates(self) -> list[dict]:
        with SessionLocal() as db:
            credentials = get_bale_credentials(db)
        if credentials is None:
            return []
        _, token, _ = credentials
        payload: dict[str, int] = {"timeout": 0, "limit": 50}
        if self.offset is not None:
            payload["offset"] = self.offset
        req = request.Request(
            f"https://tapi.bale.ai/bot{token}/getUpdates",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
        if not result.get("ok") or not isinstance(result.get("result"), list):
            raise RuntimeError("Bale getUpdates rejected the polling request")
        return result["result"]

    def deliver_update(self, update_payload: dict) -> bool:
        settings = get_settings()
        with SessionLocal() as db:
            credentials = get_bale_credentials(db)
        if credentials is None:
            return False
        _, _, webhook_secret = credentials
        webhook_url = (
            f"{settings.public_base_url.rstrip('/')}{settings.api_v1_prefix}"
            f"/auth/bale/webhook/{webhook_secret}"
        )
        req = request.Request(
            webhook_url,
            data=json.dumps(update_payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=20) as response:
                return response.status == 200
        except (error.URLError, TimeoutError, OSError):
            return False


_worker = BalePollingWorker()
_worker_lock = Lock()


def start_bale_poller() -> None:
    try:
        with SessionLocal() as db:
            configured = get_bale_credentials(db) is not None
    except Exception:
        configured = False
    if not configured:
        return
    with _worker_lock:
        _worker.start()


def stop_bale_poller() -> None:
    with _worker_lock:
        _worker.stop()
