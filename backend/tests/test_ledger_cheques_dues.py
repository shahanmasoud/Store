from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.core.config import get_settings
from app.models.ledger import Cheque, ChequeEvent, LedgerEntry
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
    due_jalali_date: str | None = None,
    source_type: str = "manual",
) -> dict:
    response = client.post(
        "/api/v1/ledger/manual-entry",
        json={
            "person_id": person_id,
            "entry_type": entry_type,
            "amount_rial": amount_rial,
            "source_type": source_type,
            "jalali_date": jalali_date,
            "due_jalali_date": due_jalali_date,
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


def test_ledger_endpoint_accepts_localized_numbers_and_canonicalizes_identifiers(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    person = client.post(
        "/api/v1/persons",
        json={"name": "مشتری", "phone": " ۰۹۱۲-٣٤٥-۶۷۸۹ ", "person_type": "customer"},
        headers=auth_headers,
    ).json()
    entry = client.post(
        "/api/v1/ledger/manual-entry",
        json={
            "person_id": str(person["id"]),
            "entry_type": "debit",
            "amount_rial": "۱٬۲۳۴٬۵۶۷",
            "jalali_date": "۱۴۰۵/۰۶/۰۷",
            "local_time": "۰۹:۳۰",
        },
        headers=auth_headers,
    )

    assert person["phone"] == "0912-345-6789"
    assert entry.status_code == 201
    assert entry.json()["amount_rial"] == 1_234_567
    assert entry.json()["jalali_date"] == "1405/06/07"
    assert entry.json()["local_time"] == "09:30"


def test_ledger_endpoint_rejects_malformed_grouping(client: TestClient, auth_headers: dict[str, str]) -> None:
    person = create_person(client, auth_headers)
    response = client.post(
        "/api/v1/ledger/manual-entry",
        json={
            "person_id": person["id"],
            "entry_type": "debit",
            "amount_rial": "۱٬۲۳",
            "jalali_date": "1405/06/07",
            "local_time": "09:30",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert "جداکننده" in response.json()["detail"][0]["msg"]


def test_create_person_persists_note_and_credit_status(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/persons",
        json={
            "name": "مشتری خوش‌حساب",
            "phone": "09120000001",
            "person_type": "customer",
            "note": "  پرداخت‌ها را همیشه به‌موقع انجام می‌دهد.  ",
            "credit_status": "good",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    assert response.json()["note"] == "پرداخت‌ها را همیشه به‌موقع انجام می‌دهد."
    assert response.json()["credit_status"] == "good"
    listed = client.get("/api/v1/persons", headers=auth_headers).json()
    assert listed[0]["note"] == "پرداخت‌ها را همیشه به‌موقع انجام می‌دهد."
    assert listed[0]["credit_status"] == "good"


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
    due_entry = create_entry(
        client, auth_headers, person["id"], 1_000_000, "1405/06/10", due_jalali_date="1405/06/10"
    )
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


def test_ledger_due_date_set_change_clear_is_audited_and_controls_dues(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    person = create_person(client, auth_headers)
    entry = create_entry(client, auth_headers, person["id"], 1_000_000, "1405/06/01")
    assert entry["due_jalali_date"] is None
    assert client.get("/api/v1/dues?jalali_date_to=1405/12/29", headers=auth_headers).json()[
        "open_ledger_entries"
    ] == []

    set_due = client.patch(
        f"/api/v1/ledger/entries/{entry['id']}/due-date",
        json={"due_jalali_date": "۱۴۰۵/۰۶/۲۰", "reason": "  توافق اولیه  "},
        headers=auth_headers,
    )
    assert set_due.status_code == 200
    assert set_due.json()["due_jalali_date"] == "1405/06/20"
    assert [item["id"] for item in client.get(
        "/api/v1/dues?jalali_date_to=1405/06/20", headers=auth_headers
    ).json()["open_ledger_entries"]] == [entry["id"]]

    changed = client.patch(
        f"/api/v1/ledger/entries/{entry['id']}/due-date",
        json={"due_jalali_date": "1405/06/25", "reason": "تمدید با مشتری"},
        headers=auth_headers,
    )
    cleared = client.patch(
        f"/api/v1/ledger/entries/{entry['id']}/due-date",
        json={"due_jalali_date": None, "reason": "حذف موعد اشتباه"},
        headers=auth_headers,
    )
    assert changed.status_code == 200
    assert cleared.status_code == 200
    assert cleared.json()["due_jalali_date"] is None

    audits = client.get(
        f"/api/v1/ledger/entries/{entry['id']}/due-date/audits", headers=auth_headers
    )
    assert audits.status_code == 200
    assert [item["before_due_date"] for item in audits.json()] == [None, "1405/06/20", "1405/06/25"]
    assert [item["after_due_date"] for item in audits.json()] == ["1405/06/20", "1405/06/25", None]
    assert [item["reason"] for item in audits.json()] == ["توافق اولیه", "تمدید با مشتری", "حذف موعد اشتباه"]
    assert all(item["actor_user_id"] == 1 for item in audits.json())
    assert all(item["actor_username"] == "admin" for item in audits.json())
    assert all(item["actor_full_name"] == "System Admin" for item in audits.json())
    assert [item["id"] for item in audits.json()] == sorted(item["id"] for item in audits.json())


def test_ledger_due_date_rejects_invalid_noop_and_ineligible_entries(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
) -> None:
    person = create_person(client, auth_headers)
    open_entry = create_entry(
        client, auth_headers, person["id"], 1000, "1405/06/01", due_jalali_date="1405/06/20"
    )
    invalid = client.patch(
        f"/api/v1/ledger/entries/{open_entry['id']}/due-date",
        json={"due_jalali_date": "1405/13/01", "reason": "اصلاح"},
        headers=auth_headers,
    )
    blank_reason = client.patch(
        f"/api/v1/ledger/entries/{open_entry['id']}/due-date",
        json={"due_jalali_date": "1405/06/21", "reason": "   "},
        headers=auth_headers,
    )
    no_op = client.patch(
        f"/api/v1/ledger/entries/{open_entry['id']}/due-date",
        json={"due_jalali_date": "1405/06/20", "reason": "بدون تغییر"},
        headers=auth_headers,
    )
    missing = client.patch(
        "/api/v1/ledger/entries/99999/due-date",
        json={"due_jalali_date": "1405/06/20", "reason": "اصلاح"},
        headers=auth_headers,
    )
    assert invalid.status_code == 422
    assert blank_reason.status_code == 422
    assert no_op.status_code == 409
    assert missing.status_code == 404

    ineligible_ids = []
    for source_type in ("sale", "manual", "manual"):
        item = create_entry(client, auth_headers, person["id"], 1000, "1405/06/01", source_type=source_type)
        ineligible_ids.append(item["id"])
    settled = db_session.get(LedgerEntry, ineligible_ids[1])
    settled.status = "settled"
    settled.remaining_rial = 0
    inactive = db_session.get(LedgerEntry, ineligible_ids[2])
    inactive.is_active = False
    db_session.commit()

    for entry_id in ineligible_ids:
        response = client.patch(
            f"/api/v1/ledger/entries/{entry_id}/due-date",
            json={"due_jalali_date": "1405/06/20", "reason": "اصلاح"},
            headers=auth_headers,
        )
        assert response.status_code == 409


def test_ledger_due_date_routes_require_superuser(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
) -> None:
    person = create_person(client, auth_headers)
    entry = create_entry(client, auth_headers, person["id"], 1000, "1405/06/01")
    db_session.add(
        User(
            username="operator-due",
            full_name="کاربر عادی",
            hashed_password=get_password_hash("operator123"),
            is_active=True,
            is_superuser=False,
        )
    )
    db_session.commit()
    login = client.post("/api/v1/auth/login", json={"username": "operator-due", "password": "operator123"})
    operator_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    payload = {"due_jalali_date": "1405/06/20", "reason": "تعیین موعد"}

    assert client.patch(f"/api/v1/ledger/entries/{entry['id']}/due-date", json=payload).status_code == 401
    assert client.get(f"/api/v1/ledger/entries/{entry['id']}/due-date/audits").status_code == 401
    forbidden_patch = client.patch(
        f"/api/v1/ledger/entries/{entry['id']}/due-date", json=payload, headers=operator_headers
    )
    forbidden_history = client.get(
        f"/api/v1/ledger/entries/{entry['id']}/due-date/audits", headers=operator_headers
    )
    assert forbidden_patch.status_code == 403
    assert forbidden_history.status_code == 403


def test_cheque_update_is_optimistic_and_audited(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    person = create_person(client, auth_headers)
    created = client.post(
        "/api/v1/cheques",
        json={
            "cheque_type": "received",
            "person_id": person["id"],
            "bank_name": "ملی",
            "cheque_number": "۱۲۳۴۵۶",
            "amount_rial": "۲٬۰۰۰٬۰۰۰",
            "issue_jalali_date": "۱۴۰۵/۰۶/۰۱",
            "due_jalali_date": "۱۴۰۵/۰۶/۲۰",
            "local_time": "۱۰:۰۰",
            "note": "نسخه اولیه",
        },
        headers=auth_headers,
    )
    assert created.status_code == 201
    cheque = created.json()
    assert cheque["cheque_number"] == "123456"
    assert cheque["amount_rial"] == 2_000_000
    assert cheque["updated_at_utc"]

    updated = client.patch(
        f"/api/v1/cheques/{cheque['id']}",
        json={
            "bank_name": "ملت",
            "amount_rial": "۲٬۵۰۰٬۰۰۰",
            "due_jalali_date": "۱۴۰۵/۰۶/۲۵",
            "note": None,
            "reason": "اصلاح اطلاعات روی برگه",
            "expected_updated_at": cheque["updated_at_utc"],
        },
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["bank_name"] == "ملت"
    assert updated.json()["amount_rial"] == 2_500_000
    assert updated.json()["due_jalali_date"] == "1405/06/25"
    assert updated.json()["note"] is None
    assert updated.json()["updated_at_utc"] != cheque["updated_at_utc"]

    stale = client.patch(
        f"/api/v1/cheques/{cheque['id']}",
        json={
            "bank_name": "تجارت",
            "reason": "فرم قدیمی",
            "expected_updated_at": cheque["updated_at_utc"],
        },
        headers=auth_headers,
    )
    assert stale.status_code == 409
    assert "دوباره دریافت" in stale.json()["detail"]

    audits = client.get(f"/api/v1/cheques/{cheque['id']}/audits", headers=auth_headers)
    assert audits.status_code == 200
    assert [item["action"] for item in audits.json()] == ["create", "update"]
    assert audits.json()[0]["before_json"] is None
    assert audits.json()[0]["after_json"]["bank_name"] == "ملی"
    assert audits.json()[1]["before_json"]["amount_rial"] == 2_000_000
    assert audits.json()[1]["after_json"]["amount_rial"] == 2_500_000
    assert audits.json()[1]["reason"] == "اصلاح اطلاعات روی برگه"
    assert all(item["actor_username"] == "admin" for item in audits.json())
    assert all(item["actor_full_name"] == "System Admin" for item in audits.json())


def test_cheque_update_rejects_noop_invalid_person_dates_and_non_pending(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    created = client.post(
        "/api/v1/cheques",
        json={
            "cheque_type": "paid",
            "bank_name": "ملی",
            "cheque_number": "update-rules",
            "amount_rial": 1_000_000,
            "issue_jalali_date": "1405/06/10",
            "due_jalali_date": "1405/06/20",
            "local_time": "10:00",
        },
        headers=auth_headers,
    ).json()
    base = {
        "reason": "اصلاح",
        "expected_updated_at": created["updated_at_utc"],
    }
    no_op = client.patch(
        f"/api/v1/cheques/{created['id']}", json={**base, "bank_name": "ملی"}, headers=auth_headers
    )
    invalid_dates = client.patch(
        f"/api/v1/cheques/{created['id']}",
        json={**base, "issue_jalali_date": "1405/07/01"},
        headers=auth_headers,
    )
    missing_person = client.patch(
        f"/api/v1/cheques/{created['id']}", json={**base, "person_id": 99999}, headers=auth_headers
    )
    inactive_person = create_person(client, auth_headers)
    assert client.delete(f"/api/v1/persons/{inactive_person['id']}", headers=auth_headers).status_code == 204
    inactive_person_response = client.patch(
        f"/api/v1/cheques/{created['id']}",
        json={**base, "person_id": inactive_person["id"]},
        headers=auth_headers,
    )
    blank_reason = client.patch(
        f"/api/v1/cheques/{created['id']}",
        json={**base, "bank_name": "ملت", "reason": "   "},
        headers=auth_headers,
    )
    assert no_op.status_code == 409
    assert invalid_dates.status_code == 422
    assert missing_person.status_code == 404
    assert inactive_person_response.status_code == 404
    assert blank_reason.status_code == 422

    canceled = client.post(
        f"/api/v1/cheques/{created['id']}/events",
        json={"event_type": "canceled", "jalali_date": "1405/06/21", "local_time": "10:00", "note": "ابطال"},
        headers=auth_headers,
    )
    assert canceled.status_code == 200
    assert canceled.json()["is_active"] is False
    rejected = client.patch(
        f"/api/v1/cheques/{created['id']}",
        json={
            "bank_name": "ملت",
            "reason": "پس از ابطال",
            "expected_updated_at": canceled.json()["updated_at_utc"],
        },
        headers=auth_headers,
    )
    assert rejected.status_code == 409
    listed = client.get("/api/v1/cheques", headers=auth_headers).json()
    assert any(item["id"] == created["id"] and item["status"] == "canceled" for item in listed)
    audits = client.get(f"/api/v1/cheques/{created['id']}/audits", headers=auth_headers).json()
    assert [item["action"] for item in audits] == ["create", "event"]
    assert audits[-1]["before_json"]["status"] == "pending"
    assert audits[-1]["after_json"]["status"] == "canceled"
    assert audits[-1]["after_json"]["is_active"] is False
    assert audits[-1]["actor_username"] == "admin"


def test_cheque_mutations_and_audits_require_superuser(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
) -> None:
    payload = {
        "cheque_type": "received",
        "bank_name": "ملی",
        "cheque_number": "role-check",
        "amount_rial": 1000,
        "issue_jalali_date": "1405/06/01",
        "due_jalali_date": "1405/06/20",
        "local_time": "10:00",
    }
    assert client.post("/api/v1/cheques", json=payload).status_code == 401
    created = client.post("/api/v1/cheques", json=payload, headers=auth_headers).json()
    db_session.add(
        User(
            username="cheque-operator",
            full_name="کاربر چک",
            hashed_password=get_password_hash("operator123"),
            is_active=True,
            is_superuser=False,
        )
    )
    db_session.commit()
    login = client.post("/api/v1/auth/login", json={"username": "cheque-operator", "password": "operator123"})
    operator_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.post("/api/v1/cheques", json=payload, headers=operator_headers).status_code == 403
    assert client.patch(
        f"/api/v1/cheques/{created['id']}",
        json={"bank_name": "ملت", "reason": "اصلاح", "expected_updated_at": created["updated_at_utc"]},
        headers=operator_headers,
    ).status_code == 403
    assert client.post(
        f"/api/v1/cheques/{created['id']}/events",
        json={"event_type": "cleared", "jalali_date": "1405/06/21", "local_time": "10:00"},
        headers=operator_headers,
    ).status_code == 403
    assert client.get(f"/api/v1/cheques/{created['id']}/audits", headers=operator_headers).status_code == 403


def test_cheque_events_have_deterministic_business_order(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
) -> None:
    created = client.post(
        "/api/v1/cheques",
        json={
            "cheque_type": "received",
            "bank_name": "ملی",
            "cheque_number": "ordered-events",
            "amount_rial": 1000,
            "issue_jalali_date": "1405/06/01",
            "due_jalali_date": "1405/06/20",
            "local_time": "10:00",
        },
        headers=auth_headers,
    ).json()
    db_session.add_all(
        [
            ChequeEvent(cheque_id=created["id"], event_type="bounced", jalali_date="1405/06/12", local_time="09:00"),
            ChequeEvent(cheque_id=created["id"], event_type="cleared", jalali_date="1405/06/11", local_time="11:00"),
        ]
    )
    db_session.commit()
    db_session.expire_all()
    item = next(item for item in client.get("/api/v1/cheques", headers=auth_headers).json() if item["id"] == created["id"])
    assert [(event["jalali_date"], event["local_time"]) for event in item["events"]] == [
        ("1405/06/01", "10:00"),
        ("1405/06/11", "11:00"),
        ("1405/06/12", "09:00"),
    ]


def test_0015_migration_backfills_legacy_snapshot_without_changing_cheque(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "legacy-cheque.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    get_settings.cache_clear()
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "0014_ledger_due_dates")
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    timestamp = "2026-09-01 08:00:00.000000"
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO cheques
                    (id, cheque_type, person_id, bank_name, cheque_number, amount_rial,
                     issue_jalali_date, due_jalali_date, status, note, is_active,
                     created_at_utc, updated_at_utc)
                VALUES
                    (77, 'received', NULL, 'ملی', 'legacy-77', 123000,
                     '1405/05/01', '1405/06/01', 'pending', 'قدیمی', 1,
                     :timestamp, NULL)
                """
            ),
            {"timestamp": timestamp},
        )
    command.upgrade(config, "head")
    with engine.connect() as connection:
        cheque = connection.execute(text("SELECT * FROM cheques WHERE id = 77")).mappings().one()
        audit = connection.execute(text("SELECT * FROM cheque_audits WHERE cheque_id = 77")).mappings().one()
        integrity = connection.execute(text("PRAGMA integrity_check")).scalar_one()
    assert integrity == "ok"
    assert cheque["amount_rial"] == 123000
    assert cheque["status"] == "pending"
    assert cheque["updated_at_utc"] == timestamp
    assert audit["action"] == "legacy_snapshot"
    assert audit["actor_user_id"] is None
    assert '"cheque_number": "legacy-77"' in audit["after_json"]
    get_settings.cache_clear()


def test_due_reminders_group_boundaries_totals_nullable_person_and_stable_order(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    person = create_person(client, auth_headers)
    overdue_ledger = create_entry(
        client, auth_headers, person["id"], 1_000_000, "1405/06/01", "debit", due_jalali_date="1405/06/09"
    )
    today_ledger = create_entry(
        client, auth_headers, person["id"], 400_000, "1405/06/02", "credit", due_jalali_date="1405/06/10"
    )
    upcoming_cheque = client.post(
        "/api/v1/cheques",
        json={
            "cheque_type": "received", "person_id": None, "bank_name": "ملت",
            "cheque_number": "reminder-1", "amount_rial": 750_000,
            "issue_jalali_date": "1405/06/01", "due_jalali_date": "1405/06/15",
            "local_time": "09:00", "note": "چک بدون شخص",
        },
        headers=auth_headers,
    ).json()
    same_day_cheque = client.post(
        "/api/v1/cheques",
        json={
            "cheque_type": "paid", "person_id": person["id"], "bank_name": "ملی",
            "cheque_number": "reminder-2", "amount_rial": 250_000,
            "issue_jalali_date": "1405/06/01", "due_jalali_date": "1405/06/10", "local_time": "09:00",
        },
        headers=auth_headers,
    ).json()

    response = client.get(
        "/api/v1/due-reminders?today_jalali=۱۴۰۵/۰۶/۱۰&through_jalali=۱۴۰۵/۰۶/۱۵",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["today_jalali"] == "1405/06/10"
    assert [(item["kind"], item["record_id"]) for item in data["overdue"]["items"]] == [
        ("ledger_entry", overdue_ledger["id"])
    ]
    assert [(item["kind"], item["record_id"]) for item in data["today"]["items"]] == [
        ("cheque", same_day_cheque["id"]), ("ledger_entry", today_ledger["id"])
    ]
    assert [(item["kind"], item["record_id"]) for item in data["upcoming"]["items"]] == [
        ("cheque", upcoming_cheque["id"])
    ]
    assert data["upcoming"]["items"][0] == {
        "kind": "cheque", "record_id": upcoming_cheque["id"], "person_id": None, "person_name": None,
        "direction": "receivable", "record_type": "received", "amount_rial": 750_000,
        "due_jalali_date": "1405/06/15", "status": "pending", "description": "چک بدون شخص",
        "cheque_number": "reminder-1", "bank_name": "ملت",
    }
    assert data["totals"] == {
        "count": 4, "total_rial": 2_400_000,
        "receivable_count": 2, "receivable_total_rial": 1_750_000,
        "payable_count": 2, "payable_total_rial": 650_000,
    }
    assert data["today"]["count"] == 2
    assert data["today"]["total_rial"] == 650_000


def test_due_reminders_exclusions_auth_range_and_query_count(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
) -> None:
    person = create_person(client, auth_headers)
    create_entry(client, auth_headers, person["id"], 100, "1405/01/01")
    future = create_entry(
        client, auth_headers, person["id"], 200, "1405/01/01", due_jalali_date="1405/07/01"
    )
    settled = create_entry(
        client, auth_headers, person["id"], 300, "1405/01/01", due_jalali_date="1405/06/05"
    )
    inactive = create_entry(
        client, auth_headers, person["id"], 400, "1405/01/01", due_jalali_date="1405/06/05"
    )
    db_session.get(LedgerEntry, settled["id"]).status = "settled"
    db_session.get(LedgerEntry, settled["id"]).remaining_rial = 0
    db_session.get(LedgerEntry, inactive["id"]).is_active = False
    db_session.commit()
    cleared = client.post(
        "/api/v1/cheques",
        json={
            "cheque_type": "received", "bank_name": "ملی", "cheque_number": "excluded-cleared",
            "amount_rial": 500, "issue_jalali_date": "1405/06/01",
            "due_jalali_date": "1405/06/05", "local_time": "09:00",
        },
        headers=auth_headers,
    ).json()
    client.post(
        f"/api/v1/cheques/{cleared['id']}/events",
        json={"event_type": "cleared", "jalali_date": "1405/06/06", "local_time": "09:00"},
        headers=auth_headers,
    )

    assert client.get(
        "/api/v1/due-reminders?today_jalali=1405/06/10&through_jalali=1405/06/20"
    ).status_code == 401
    assert client.get(
        "/api/v1/due-reminders?today_jalali=1405/06/20&through_jalali=1405/06/10", headers=auth_headers
    ).status_code == 422
    assert client.get(
        "/api/v1/due-reminders?today_jalali=1405/13/01&through_jalali=1405/13/02", headers=auth_headers
    ).status_code == 422

    statement_count = 0

    def count_statement(*_args) -> None:
        nonlocal statement_count
        statement_count += 1

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", count_statement)
    try:
        response = client.get(
            "/api/v1/due-reminders?today_jalali=1405/06/10&through_jalali=1405/06/20", headers=auth_headers
        )
    finally:
        event.remove(engine, "before_cursor_execute", count_statement)
    assert response.status_code == 200
    assert response.json()["totals"]["count"] == 0
    assert future["id"] not in [
        item["record_id"]
        for group in ("overdue", "today", "upcoming")
        for item in response.json()[group]["items"]
    ]
    # One auth lookup plus one joined query per financial source; no person N+1 queries.
    assert statement_count == 3


def test_person_update_validation_and_soft_delete_preserve_financial_history(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    person = create_person(client, auth_headers)
    debit = create_entry(client, auth_headers, person["id"], 1_200_000, "1405/06/01", "debit")
    create_entry(client, auth_headers, person["id"], 250_000, "1405/06/02", "credit")

    updated = client.patch(
        f"/api/v1/persons/{person['id']}",
        json={"name": "  مشتری نمونه  ", "note": "  پرداخت منظم  ", "credit_status": "good"},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert {
        key: updated.json()[key] for key in ("name", "note", "credit_status", "is_active")
    } == {"name": "مشتری نمونه", "note": "پرداخت منظم", "credit_status": "good", "is_active": True}

    invalid = client.patch(
        f"/api/v1/persons/{person['id']}",
        json={"credit_status": "unknown"},
        headers=auth_headers,
    )
    assert invalid.status_code == 422
    assert "وضعیت" in invalid.json()["detail"][0]["msg"]
    assert client.patch(
        f"/api/v1/persons/{person['id']}", json={"name": None}, headers=auth_headers
    ).status_code == 422

    before = client.get(f"/api/v1/ledger/persons/{person['id']}/summary", headers=auth_headers)
    reports_before = (
        client.get("/api/v1/reports/cashflow?jalali_date_to=1405/06/30", headers=auth_headers).json(),
        client.get("/api/v1/reports/customer-debts", headers=auth_headers).json(),
    )
    assert before.status_code == 200
    assert before.json() == {
        "person_id": person["id"],
        "debit_open_rial": 1_200_000,
        "credit_open_rial": 250_000,
        "net_balance_rial": 950_000,
        "open_entries_count": 2,
    }

    deleted = client.delete(f"/api/v1/persons/{person['id']}", headers=auth_headers)
    deleted_again = client.delete(f"/api/v1/persons/{person['id']}", headers=auth_headers)
    assert deleted.status_code == 204
    assert deleted_again.status_code == 204
    assert client.get("/api/v1/persons", headers=auth_headers).json() == []
    inactive = client.get("/api/v1/persons?include_inactive=true", headers=auth_headers).json()
    assert inactive[0]["is_active"] is False

    ledger = client.get(f"/api/v1/ledger/persons/{person['id']}", headers=auth_headers)
    after = client.get(f"/api/v1/ledger/persons/{person['id']}/summary", headers=auth_headers)
    assert ledger.status_code == 200
    assert ledger.json()[0]["id"] == debit["id"]
    assert after.json() == before.json()
    reports_after = (
        client.get("/api/v1/reports/cashflow?jalali_date_to=1405/06/30", headers=auth_headers).json(),
        client.get("/api/v1/reports/customer-debts", headers=auth_headers).json(),
    )
    assert reports_after == reports_before

    assert client.patch(
        f"/api/v1/persons/{person['id']}", json={"name": "ویرایش"}, headers=auth_headers
    ).status_code == 404
    assert client.post(
        "/api/v1/ledger/manual-entry",
        json={
            "person_id": person["id"],
            "entry_type": "debit",
            "amount_rial": 100,
            "jalali_date": "1405/06/03",
            "local_time": "10:00",
        },
        headers=auth_headers,
    ).status_code == 404


def test_person_and_ledger_routes_require_admin_auth(client: TestClient, auth_headers: dict[str, str]) -> None:
    person = create_person(client, auth_headers)
    requests = [
        client.get("/api/v1/persons"),
        client.post("/api/v1/persons", json={"name": "الف", "person_type": "customer"}),
        client.patch(f"/api/v1/persons/{person['id']}", json={"name": "ب"}),
        client.delete(f"/api/v1/persons/{person['id']}"),
        client.get(f"/api/v1/ledger/persons/{person['id']}/summary"),
        client.get(f"/api/v1/ledger/persons/{person['id']}"),
        client.post("/api/v1/ledger/manual-entry", json={}),
    ]
    assert all(response.status_code == 401 for response in requests)


def test_only_superuser_can_update_or_deactivate_person(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
) -> None:
    person = create_person(client, auth_headers)
    db_session.add(
        User(
            username="operator",
            full_name="کاربر عادی",
            hashed_password=get_password_hash("operator123"),
            is_active=True,
            is_superuser=False,
        )
    )
    db_session.commit()
    login = client.post("/api/v1/auth/login", json={"username": "operator", "password": "operator123"})
    operator_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    patch_response = client.patch(
        f"/api/v1/persons/{person['id']}", json={"name": "نام جدید"}, headers=operator_headers
    )
    delete_response = client.delete(f"/api/v1/persons/{person['id']}", headers=operator_headers)

    assert patch_response.status_code == 403
    assert delete_response.status_code == 403
    assert patch_response.json()["detail"] == "شما اجازه دسترسی به این بخش را ندارید."
    assert delete_response.json()["detail"] == "شما اجازه دسترسی به این بخش را ندارید."
