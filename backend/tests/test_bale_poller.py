import json
from urllib import error

from app.core.config import get_settings
from app.scripts import configure_bale_webhook
from app.services import bale_poller


class FakeResponse:
    def __init__(self, payload: dict, status: int = 200) -> None:
        self.payload = payload
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def configure_settings(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "bale_bot_token", "poll-test-token")
    monkeypatch.setattr(settings, "bale_bot_username", "HStoreBot")
    monkeypatch.setattr(settings, "bale_webhook_secret", "poll-test-secret")
    monkeypatch.setattr(settings, "public_base_url", "https://store.example")
    monkeypatch.setattr(settings, "bale_polling_fallback", True)


def test_fetch_updates_uses_offset_and_long_poll(monkeypatch) -> None:
    configure_settings(monkeypatch)
    captured = {}

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["payload"] = json.loads(req.data)
        captured["timeout"] = timeout
        return FakeResponse({"ok": True, "result": [{"update_id": 42}]})

    monkeypatch.setattr(bale_poller.request, "urlopen", fake_urlopen)
    worker = bale_poller.BalePollingWorker()
    worker.offset = 42

    assert worker.fetch_updates() == [{"update_id": 42}]
    assert captured["url"].endswith("/getUpdates")
    assert captured["payload"] == {"timeout": 20, "limit": 50, "offset": 42}
    assert captured["timeout"] == 25


def test_deliver_update_retries_network_failure(monkeypatch) -> None:
    configure_settings(monkeypatch)

    def failed_urlopen(_req, timeout):
        raise error.URLError("offline")

    monkeypatch.setattr(bale_poller.request, "urlopen", failed_urlopen)
    worker = bale_poller.BalePollingWorker()

    assert worker.deliver_update({"update_id": 1}) is False


def test_configure_script_disables_webhook_in_polling_mode(monkeypatch) -> None:
    configure_settings(monkeypatch)
    calls = []

    def fake_call(method: str, payload: dict | None = None) -> dict:
        calls.append((method, payload))
        if method == "getMe":
            return {"ok": True, "result": {"username": "HStoreBot"}}
        return {"ok": True, "result": True}

    monkeypatch.setattr(configure_bale_webhook, "call_bale", fake_call)

    configure_bale_webhook.main()

    assert calls == [("getMe", None), ("setWebhook", {"url": ""})]
