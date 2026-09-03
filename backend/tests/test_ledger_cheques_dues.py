from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User

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
        db.add(
            User(
                username="admin",
                full_name="System Admin",
                hashed_password=get_password_hash("admin123"),
                is_active=True,
                is_superuser=True,
            )
        )
        db.commit()
        yield db

    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_person(client: TestClient, auth_headers: dict[str, str]) -> dict:
    response = client.post(
        "/api/v1/persons",
        json={"name": "Customer One", "phone": "09120000000", "person_type": "customer"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()


def create_entry(
    client: TestClient,
    auth_headers: dict[str, str],
    person_id: int,
    amount_rial: int,
    jalali_date: str,
    entry_type: str = "debit",
) -> dict:
    response = client.post(
        "/api/v1/ledger/manual-entry",
        json={
            "person_id": person_id,
            "entry_type": entry_type,
            "amount_rial": amount_rial,
            "jalali_date": jalali_date,
            "local_time": "10:00",
            "description": "Manual opening balance",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()


def test_person_and_manual_debit_credit_entries(client: TestClient, auth_headers: dict[str, str]) -> None:
    person = create_person(client, auth_headers)
    debit = create_entry(client, auth_headers, person["id"], 1_000_000, "1405/06/01", "debit")
    credit = create_entry(client, auth_headers, person["id"], 500_000, "1405/06/02", "credit")

    ledger = client.get(f"/api/v1/ledger/persons/{person['id']}", headers=auth_headers)

    assert debit["entry_type"] == "debit"
    assert debit["remaining_rial"] == 1_000_000
    assert credit["entry_type"] == "credit"
    assert credit["remaining_rial"] == 500_000
    assert ledger.status_code == 200
    assert [entry["id"] for entry in ledger.json()] == [debit["id"], credit["id"]]


def test_settlement_reduces_oldest_open_entries_and_marks_settled(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    person = create_person(client, auth_headers)
    old_entry = create_entry(client, auth_headers, person["id"], 1_000_000, "1405/06/01")
    new_entry = create_entry(client, auth_headers, person["id"], 750_000, "1405/06/05")

    response = client.post(
        "/api/v1/settlements",
        json={
            "person_id": person["id"],
            "amount_rial": 1_250_000,
            "jalali_date": "1405/06/10",
            "local_time": "12:30",
            "note": "Cash received",
        },
        headers=auth_headers,
    )
    ledger = client.get(f"/api/v1/ledger/persons/{person['id']}", headers=auth_headers).json()

    assert response.status_code == 201
    by_id = {entry["id"]: entry for entry in ledger}
    assert by_id[old_entry["id"]]["remaining_rial"] == 0
    assert by_id[old_entry["id"]]["status"] == "settled"
    assert by_id[new_entry["id"]]["remaining_rial"] == 500_000
    assert by_id[new_entry["id"]]["status"] == "open"


def test_over_settlement_returns_409(client: TestClient, auth_headers: dict[str, str]) -> None:
    person = create_person(client, auth_headers)
    create_entry(client, auth_headers, person["id"], 500_000, "1405/06/01")

    response = client.post(
        "/api/v1/settlements",
        json={
            "person_id": person["id"],
            "amount_rial": 600_000,
            "jalali_date": "1405/06/02",
            "local_time": "09:00",
        },
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "مبلغ تسویه از مانده بدهکار بیشتر است."


def test_settlement_only_consumes_selected_side_for_mixed_ledger(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    person = create_person(client, auth_headers)
    debit = create_entry(client, auth_headers, person["id"], 1_000_000, "1405/06/01", "debit")
    credit = create_entry(client, auth_headers, person["id"], 500_000, "1405/06/02", "credit")

    too_much_credit = client.post(
        "/api/v1/settlements",
        json={
            "person_id": person["id"],
            "entry_type": "credit",
            "amount_rial": 700_000,
            "jalali_date": "1405/06/10",
            "local_time": "12:30",
        },
        headers=auth_headers,
    )
    assert too_much_credit.status_code == 409

    settled = client.post(
        "/api/v1/settlements",
        json={
            "person_id": person["id"],
            "entry_type": "credit",
            "amount_rial": 400_000,
            "jalali_date": "1405/06/10",
            "local_time": "12:30",
        },
        headers=auth_headers,
    )
    ledger = client.get(f"/api/v1/ledger/persons/{person['id']}", headers=auth_headers).json()
    by_id = {entry["id"]: entry for entry in ledger}

    assert settled.status_code == 201
    assert settled.json()["entry_type"] == "credit"
    assert by_id[debit["id"]]["remaining_rial"] == 1_000_000
    assert by_id[credit["id"]]["remaining_rial"] == 100_000


def test_cheque_lifecycle_events_update_status_and_append_events(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    person = create_person(client, auth_headers)
    created = client.post(
        "/api/v1/cheques",
        json={
            "cheque_type": "received",
            "person_id": person["id"],
            "bank_name": "Melli",
            "cheque_number": "123456",
            "amount_rial": 2_000_000,
            "issue_jalali_date": "1405/06/01",
            "due_jalali_date": "1405/06/20",
            "local_time": "10:00",
            "note": "Customer cheque",
        },
        headers=auth_headers,
    )

    assert created.status_code == 201
    cheque_id = created.json()["id"]
    assert created.json()["status"] == "pending"
    assert [event["event_type"] for event in created.json()["events"]] == ["created"]

    cleared = client.post(
        f"/api/v1/cheques/{cheque_id}/events",
        json={"event_type": "cleared", "jalali_date": "1405/06/21", "local_time": "11:00"},
        headers=auth_headers,
    )

    assert cleared.status_code == 200
    assert cleared.json()["status"] == "cleared"
    assert [event["event_type"] for event in cleared.json()["events"]] == ["created", "cleared"]

    repeated = client.post(
        f"/api/v1/cheques/{cheque_id}/events",
        json={"event_type": "bounced", "jalali_date": "1405/06/22", "local_time": "11:00"},
        headers=auth_headers,
    )
    assert repeated.status_code == 409
    assert repeated.json()["detail"] == "این تغییر وضعیت برای چک مجاز نیست."


def test_cheque_rejects_invalid_date_order_and_early_event(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    invalid = client.post(
        "/api/v1/cheques",
        json={
            "cheque_type": "paid",
            "bank_name": "Melli",
            "cheque_number": "date-order",
            "amount_rial": 1_000_000,
            "issue_jalali_date": "1405/06/10",
            "due_jalali_date": "1405/06/01",
            "local_time": "10:00",
        },
        headers=auth_headers,
    )
    assert invalid.status_code == 422

    created = client.post(
        "/api/v1/cheques",
        json={
            "cheque_type": "paid",
            "bank_name": "Melli",
            "cheque_number": "early-event",
            "amount_rial": 1_000_000,
            "issue_jalali_date": "1405/06/10",
            "due_jalali_date": "1405/06/20",
            "local_time": "10:00",
        },
        headers=auth_headers,
    ).json()
    event = client.post(
        f"/api/v1/cheques/{created['id']}/events",
        json={"event_type": "cleared", "jalali_date": "1405/06/09", "local_time": "11:00"},
        headers=auth_headers,
    )
    assert event.status_code == 422
    assert event.json()["detail"] == "تاریخ اقدام نمی‌تواند پیش از آخرین رویداد چک باشد."


def test_bounced_cheque_can_clear_later_but_event_dates_cannot_go_back(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    created = client.post(
        "/api/v1/cheques",
        json={
            "cheque_type": "received",
            "bank_name": "Mellat",
            "cheque_number": "bounce-then-clear",
            "amount_rial": 2_000_000,
            "issue_jalali_date": "1405/06/01",
            "due_jalali_date": "1405/06/10",
            "local_time": "10:00",
        },
        headers=auth_headers,
    ).json()
    bounced = client.post(
        f"/api/v1/cheques/{created['id']}/events",
        json={"event_type": "bounced", "jalali_date": "1405/06/11", "local_time": "11:00"},
        headers=auth_headers,
    )
    assert bounced.status_code == 200
    assert bounced.json()["status"] == "bounced"

    early_clear = client.post(
        f"/api/v1/cheques/{created['id']}/events",
        json={"event_type": "cleared", "jalali_date": "1405/06/10", "local_time": "12:00"},
        headers=auth_headers,
    )
    assert early_clear.status_code == 422

    same_day_early_time = client.post(
        f"/api/v1/cheques/{created['id']}/events",
        json={"event_type": "cleared", "jalali_date": "1405/06/11", "local_time": "10:59"},
        headers=auth_headers,
    )
    assert same_day_early_time.status_code == 422

    cleared = client.post(
        f"/api/v1/cheques/{created['id']}/events",
        json={"event_type": "cleared", "jalali_date": "1405/06/12", "local_time": "12:00"},
        headers=auth_headers,
    )
    assert cleared.status_code == 200
    assert cleared.json()["status"] == "cleared"
    assert [item["event_type"] for item in cleared.json()["events"]] == ["created", "bounced", "cleared"]


def test_dues_returns_open_ledger_and_pending_cheques_up_to_date(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    person = create_person(client, auth_headers)
    due_entry = create_entry(client, auth_headers, person["id"], 1_000_000, "1405/06/10")
    create_entry(client, auth_headers, person["id"], 1_000_000, "1405/07/01")
    cheque = client.post(
        "/api/v1/cheques",
        json={
            "cheque_type": "received",
            "person_id": person["id"],
            "bank_name": "Melli",
            "cheque_number": "654321",
            "amount_rial": 3_000_000,
            "issue_jalali_date": "1405/06/01",
            "due_jalali_date": "1405/06/30",
            "local_time": "10:00",
        },
        headers=auth_headers,
    ).json()
    client.post(
        "/api/v1/cheques",
        json={
            "cheque_type": "paid",
            "person_id": person["id"],
            "bank_name": "Saderat",
            "cheque_number": "987654",
            "amount_rial": 4_000_000,
            "issue_jalali_date": "1405/06/01",
            "due_jalali_date": "1405/07/05",
            "local_time": "10:00",
        },
        headers=auth_headers,
    )

    response = client.get("/api/v1/dues?jalali_date_to=1405/06/30", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert [entry["id"] for entry in data["open_ledger_entries"]] == [due_entry["id"]]
    assert [item["id"] for item in data["pending_cheques"]] == [cheque["id"]]
