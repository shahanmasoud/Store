from collections.abc import Generator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.security import create_access_token, decode_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.bale_auth import BaleLoginChallenge, CustomerAccount
from app.services import bale_auth as bale_service

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestingSessionLocal() as db:
        yield db
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    settings = get_settings()
    monkeypatch.setattr(settings, "bale_bot_token", "test-bot-token")
    monkeypatch.setattr(settings, "bale_bot_username", "test_store_bot")
    monkeypatch.setattr(settings, "bale_webhook_secret", "test-webhook-secret")
    monkeypatch.setattr(settings, "public_base_url", "https://store.example")

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_login_challenge(client: TestClient) -> dict:
    response = client.post("/api/v1/auth/bale/challenges", json={"return_path": "/"})
    assert response.status_code == 201
    return response.json()


def confirmation_update(code: str, *, user_id: int = 441) -> dict:
    return {
        "update_id": 1,
        "callback_query": {
            "id": "callback-1",
            "data": f"bale_login_confirm:{code}",
            "from": {
                "id": user_id,
                "first_name": "علی",
                "last_name": "رضایی",
                "username": "ali_rezaei",
            },
            "message": {"chat": {"id": user_id}},
        },
    }


def silence_gateway(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, dict]]:
    calls: list[tuple[str, dict]] = []

    def record_call(self, method: str, payload: dict) -> None:
        calls.append((method, payload))

    monkeypatch.setattr(bale_service.BaleBotGateway, "call", record_call)
    return calls


def test_create_challenge_has_two_minute_ttl_and_hashed_code(
    client: TestClient, db_session: Session
) -> None:
    data = create_login_challenge(client)

    assert data["expires_in_seconds"] == 120
    assert data["expires_at_utc"].endswith(("Z", "+00:00"))
    assert data["poll_after_seconds"] == 2
    assert data["status"] == "pending"
    assert data["code"].isdigit() and len(data["code"]) == 6
    assert data["bot_url"] == f"https://ble.ir/test_store_bot?start={data['code']}"

    stored = db_session.get(BaleLoginChallenge, data["id"])
    assert stored is not None
    assert stored.code_hash != data["code"]
    assert len(stored.code_hash) == 64
    assert 119 <= (bale_service.as_utc(stored.expires_at_utc) - bale_service.as_utc(stored.created_at_utc)).total_seconds() <= 120


@pytest.mark.parametrize("return_path", ["https://evil.example", "//evil.example/path"])
def test_create_challenge_rejects_external_return_path(
    client: TestClient, return_path: str
) -> None:
    response = client.post("/api/v1/auth/bale/challenges", json={"return_path": return_path})
    assert response.status_code == 422


def test_status_does_not_expose_code_or_bale_identity(
    client: TestClient, db_session: Session
) -> None:
    challenge = create_login_challenge(client)
    stored = db_session.get(BaleLoginChallenge, challenge["id"])
    assert stored is not None
    stored.bale_user_id = "sensitive-id"
    db_session.commit()

    response = client.get(f"/api/v1/auth/bale/challenges/{challenge['id']}")
    assert response.status_code == 200
    assert "code" not in response.json()
    assert "bale_user_id" not in response.json()


def test_webhook_rejects_wrong_secret(client: TestClient) -> None:
    response = client.post("/api/v1/auth/bale/webhook/wrong", json={"update_id": 1})
    assert response.status_code == 404


def test_webhook_handles_malformed_callback_without_server_error(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = silence_gateway(monkeypatch)
    payload = confirmation_update("not-a-code")
    response = client.post(
        "/api/v1/auth/bale/webhook/test-webhook-secret", json=payload
    )
    assert response.status_code == 200
    assert any(method == "answerCallbackQuery" for method, _ in calls)


def test_start_message_requests_confirmation(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    challenge = create_login_challenge(client)
    calls = silence_gateway(monkeypatch)

    response = client.post(
        "/api/v1/auth/bale/webhook/test-webhook-secret",
        json={
            "message": {
                "text": f"/start {challenge['code']}",
                "from": {"id": 441, "first_name": "علی"},
                "chat": {"id": 441},
            }
        },
    )

    assert response.status_code == 200
    assert calls[0][0] == "sendMessage"
    button = calls[0][1]["reply_markup"]["inline_keyboard"][0][0]
    assert button["callback_data"] == f"bale_login_confirm:{challenge['code']}"


def test_callback_approves_and_exchange_is_single_use(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    challenge = create_login_challenge(client)
    silence_gateway(monkeypatch)

    webhook_response = client.post(
        "/api/v1/auth/bale/webhook/test-webhook-secret",
        json=confirmation_update(challenge["code"]),
    )
    assert webhook_response.status_code == 200

    status_response = client.get(f"/api/v1/auth/bale/challenges/{challenge['id']}")
    assert status_response.json()["status"] == "approved"
    assert "bale_user_id" not in status_response.json()

    exchange_response = client.post(
        f"/api/v1/auth/bale/challenges/{challenge['id']}/exchange"
    )
    assert exchange_response.status_code == 200
    exchanged = exchange_response.json()
    assert exchanged["customer"]["display_name"] == "علی رضایی"
    assert exchanged["customer"]["provider"] == "bale"
    claims = decode_access_token(exchanged["access_token"])
    assert claims["actor_type"] == "customer"
    assert claims["provider"] == "bale"

    me_response = client.get(
        "/api/v1/auth/bale/me",
        headers={"Authorization": f"Bearer {exchanged['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json() == {
        "id": exchanged["customer"]["id"],
        "display_name": "علی رضایی",
        "provider": "bale",
    }

    assert db_session.query(CustomerAccount).count() == 1
    second_exchange = client.post(
        f"/api/v1/auth/bale/challenges/{challenge['id']}/exchange"
    )
    assert second_exchange.status_code == 409


def test_same_bale_identity_reuses_customer(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    silence_gateway(monkeypatch)
    for _ in range(2):
        challenge = create_login_challenge(client)
        response = client.post(
            "/api/v1/auth/bale/webhook/test-webhook-secret",
            json=confirmation_update(challenge["code"], user_id=882),
        )
        assert response.status_code == 200
        assert client.post(
            f"/api/v1/auth/bale/challenges/{challenge['id']}/exchange"
        ).status_code == 200

    assert db_session.query(CustomerAccount).count() == 1


def test_approved_challenge_identity_cannot_be_overwritten(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    challenge = create_login_challenge(client)
    silence_gateway(monkeypatch)

    first = client.post(
        "/api/v1/auth/bale/webhook/test-webhook-secret",
        json=confirmation_update(challenge["code"], user_id=441),
    )
    second = client.post(
        "/api/v1/auth/bale/webhook/test-webhook-secret",
        json=confirmation_update(challenge["code"], user_id=999),
    )

    assert first.status_code == 200
    assert second.status_code == 200
    db_session.expire_all()
    stored = db_session.get(BaleLoginChallenge, challenge["id"])
    assert stored is not None
    assert stored.status == "approved"
    assert stored.bale_user_id == "441"


def test_expired_challenge_cannot_be_exchanged(
    client: TestClient, db_session: Session
) -> None:
    challenge = create_login_challenge(client)
    stored = db_session.get(BaleLoginChallenge, challenge["id"])
    assert stored is not None
    stored.status = "approved"
    stored.bale_user_id = "441"
    stored.expires_at_utc = bale_service.utc_now() - timedelta(seconds=1)
    db_session.commit()

    status_response = client.get(f"/api/v1/auth/bale/challenges/{challenge['id']}")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "expired"
    assert client.post(
        f"/api/v1/auth/bale/challenges/{challenge['id']}/exchange"
    ).status_code == 409


def test_unconfigured_bale_login_returns_actionable_error(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "bale_bot_token", "")
    response = client.post("/api/v1/auth/bale/challenges", json={"return_path": "/"})
    assert response.status_code == 503
    assert response.json()["detail"] == "ورود با بله هنوز روی سرور پیکربندی نشده است."


def test_customer_me_rejects_missing_or_non_customer_token(client: TestClient) -> None:
    assert client.get("/api/v1/auth/bale/me").status_code == 401
    manager_token = create_access_token("admin")
    response = client.get(
        "/api/v1/auth/bale/me",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 401
