import json
from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.ledger import Cheque, ChequeAudit, LedgerActionAudit, LedgerEntry, Person
from app.models.user import User, UserAdminAudit


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    with testing_session() as db:
        db.add(
            User(
                username="admin",
                full_name="مدیر سیستم",
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


def login(client: TestClient, username: str = "admin", password: str = "admin123") -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def admin_headers(client: TestClient) -> dict[str, str]:
    return {"Authorization": f"Bearer {login(client)}"}


def create_cashier(
    client: TestClient,
    *,
    username: str = "cashier",
    password: str = "cashier-123",
    can_sales: bool = True,
    can_catalog_inventory: bool = False,
    can_ledger: bool = False,
    can_cheques_reports: bool = False,
) -> dict:
    response = client.post(
        "/api/v1/users",
        headers=admin_headers(client),
        json={
            "username": username,
            "full_name": "صندوقدار آزمایشی",
            "temporary_password": password,
            "can_sales": can_sales,
            "can_catalog_inventory": can_catalog_inventory,
            "can_ledger": can_ledger,
            "can_cheques_reports": can_cheques_reports,
            "reason": "ایجاد حساب برای شیفت فروش",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_users_require_authentication_and_superuser(client: TestClient, db_session: Session) -> None:
    assert client.get("/api/v1/users").status_code == 401
    db_session.add(
        User(
            username="plain",
            full_name="کاربر عادی",
            hashed_password="$2b$12$invalid-but-not-used",
            is_active=True,
            is_superuser=False,
        )
    )
    db_session.commit()
    # Create through the supported path so that password hashing is valid.
    plain = db_session.scalar(select(User).where(User.username == "plain"))
    plain.hashed_password = get_password_hash("plain-pass-123")
    db_session.commit()
    token = login(client, "plain", "plain-pass-123")
    response = client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


@pytest.mark.parametrize(
    "forbidden_field,forbidden_value",
    [("is_superuser", True)],
)
def test_create_user_forbids_privilege_escalation_fields(
    client: TestClient, forbidden_field: str, forbidden_value: bool
) -> None:
    payload = {
        "username": "cashier",
        "full_name": "صندوقدار",
        "temporary_password": "cashier-123",
        "can_sales": True,
        "reason": "نیاز عملیاتی فروش",
        forbidden_field: forbidden_value,
    }
    response = client.post("/api/v1/users", headers=admin_headers(client), json=payload)
    assert response.status_code == 422
    assert all(user["username"] != "cashier" for user in client.get("/api/v1/users", headers=admin_headers(client)).json())


def test_effective_permissions_and_inactive_users_are_listed(client: TestClient) -> None:
    headers = admin_headers(client)
    admin = client.get("/api/v1/auth/me", headers=headers).json()
    assert admin["can_sales"] is True
    assert admin["can_catalog_inventory"] is True
    assert admin["can_ledger"] is True
    assert admin["can_cheques_reports"] is True

    cashier = create_cashier(client)
    assert cashier["is_superuser"] is False
    assert cashier["can_sales"] is True
    assert cashier["can_catalog_inventory"] is False
    response = client.post(
        f"/api/v1/users/{cashier['id']}/deactivate",
        headers=headers,
        json={"reason": "پایان همکاری صندوقدار"},
    )
    assert response.status_code == 200
    listed = client.get("/api/v1/users", headers=headers).json()
    assert next(item for item in listed if item["id"] == cashier["id"])["is_active"] is False


def test_cashier_can_use_sales_only_and_cannot_cancel(client: TestClient) -> None:
    create_cashier(client)
    token = login(client, "cashier", "cashier-123")
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/sales", headers=headers).status_code == 200
    options = client.get("/api/v1/sales/form-options", headers=headers)
    assert options.status_code == 200
    assert set(options.json()) == {"variants", "inventory", "customers"}
    assert client.get("/api/v1/daily-journal?jalali_date=1405/06/17", headers=headers).status_code == 200
    assert client.post("/api/v1/sales/999/cancel", headers=headers).status_code == 403

    denied = [
        "/api/v1/products",
        "/api/v1/purchase-invoices",
        "/api/v1/persons",
        "/api/v1/reports/inventory",
        "/api/v1/online/channels",
    ]
    for path in denied:
        response = client.get(path, headers=headers)
        assert response.status_code == 403, (path, response.text)


def test_catalog_inventory_operator_matrix_and_adjustment_actor(client: TestClient) -> None:
    operator = create_cashier(
        client,
        username="stock",
        password="stock-pass-123",
        can_sales=False,
        can_catalog_inventory=True,
    )
    token = login(client, "stock", "stock-pass-123")
    headers = {"Authorization": f"Bearer {token}"}

    unit_response = client.post("/api/v1/units", headers=headers, json={"name": "عدد", "symbol": "عدد"})
    assert unit_response.status_code == 201, unit_response.text
    unit_id = unit_response.json()["id"]
    assert client.patch(f"/api/v1/units/{unit_id}", headers=headers, json={"name": "بسته"}).status_code == 200
    category = client.post("/api/v1/categories", headers=headers, json={"name": "آزمایشی"})
    assert category.status_code == 201
    product = client.post(
        "/api/v1/products",
        headers=headers,
        json={"name": "کالای انبار", "category_id": category.json()["id"]},
    )
    assert product.status_code == 201
    variant = client.post(
        "/api/v1/product-variants",
        headers=headers,
        json={
            "product_id": product.json()["id"],
            "unit_id": unit_id,
            "name": "کالای انبار - بسته",
            "retail_price_rial": 250000,
        },
    )
    assert variant.status_code == 201, variant.text
    variant_id = variant.json()["id"]
    adjustment = client.post(
        "/api/v1/inventory/adjustments",
        headers=headers,
        json={
            "variant_id": variant_id,
            "adjustment_type": "initial",
            "quantity": "5",
            "unit_cost_rial": 180000,
            "reason": "شمارش موجودی ابتدای شیفت",
            "jalali_date": "1405/06/17",
            "local_time": "09:15",
        },
    )
    assert adjustment.status_code == 201, adjustment.text
    assert adjustment.json()["actor_user_id"] == operator["id"]
    assert adjustment.json()["actor_username"] == "stock"
    assert client.get("/api/v1/inventory", headers=headers).status_code == 200
    assert client.get("/api/v1/inventory-transactions", headers=headers).status_code == 200
    assert client.get("/api/v1/purchase-invoices", headers=headers).status_code == 200

    # Destructive operations stay behind the primary administrator even with the section permission.
    assert client.delete(f"/api/v1/units/{unit_id}", headers=headers).status_code == 403
    assert client.delete(f"/api/v1/products/{product.json()['id']}/image", headers=headers).status_code == 403
    assert client.post("/api/v1/purchase-invoices/999/cancel", headers=headers).status_code == 403
    assert client.delete("/api/v1/price-rules/999", headers=headers).status_code == 403

    # No implicit access is gained outside the granted section.
    assert client.get("/api/v1/sales", headers=headers).status_code == 403
    assert client.get("/api/v1/persons", headers=headers).status_code == 403
    assert client.get("/api/v1/reports/inventory", headers=headers).status_code == 200
    assert client.get("/api/v1/online/channels", headers=headers).status_code == 403


def test_combined_permissions_and_catalog_permission_change_invalidate_token(client: TestClient) -> None:
    operator = create_cashier(client, can_sales=True, can_catalog_inventory=True)
    old_token = login(client, "cashier", "cashier-123")
    old_headers = {"Authorization": f"Bearer {old_token}"}
    assert client.get("/api/v1/sales", headers=old_headers).status_code == 200
    assert client.get("/api/v1/products", headers=old_headers).status_code == 200

    response = client.patch(
        f"/api/v1/users/{operator['id']}",
        headers=admin_headers(client),
        json={"can_catalog_inventory": False, "reason": "پایان مسئولیت انبار"},
    )
    assert response.status_code == 200
    assert response.json()["can_sales"] is True
    assert response.json()["can_catalog_inventory"] is False
    assert client.get("/api/v1/auth/me", headers=old_headers).status_code == 401
    fresh_headers = {"Authorization": f"Bearer {login(client, 'cashier', 'cashier-123')}"}
    assert client.get("/api/v1/sales", headers=fresh_headers).status_code == 200
    assert client.get("/api/v1/products", headers=fresh_headers).status_code == 403


def test_permission_change_invalidates_token_and_denies_new_session(client: TestClient) -> None:
    cashier = create_cashier(client)
    old_token = login(client, "cashier", "cashier-123")
    response = client.patch(
        f"/api/v1/users/{cashier['id']}",
        headers=admin_headers(client),
        json={"can_sales": False, "reason": "انتقال از صندوق فروش"},
    )
    assert response.status_code == 200
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"}).status_code == 401
    new_token = login(client, "cashier", "cashier-123")
    denied = client.get("/api/v1/sales", headers={"Authorization": f"Bearer {new_token}"})
    assert denied.status_code == 403
    assert denied.json()["detail"] == "شما اجازه دسترسی به این بخش را ندارید."


def test_reset_password_and_deactivation_invalidate_sessions(client: TestClient) -> None:
    cashier = create_cashier(client)
    old_token = login(client, "cashier", "cashier-123")
    reset = client.post(
        f"/api/v1/users/{cashier['id']}/reset-password",
        headers=admin_headers(client),
        json={"temporary_password": "replacement-456", "reason": "درخواست بازنشانی امن"},
    )
    assert reset.status_code == 200
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"username": "cashier", "password": "cashier-123"}).status_code == 401
    fresh_token = login(client, "cashier", "replacement-456")

    deactivated = client.post(
        f"/api/v1/users/{cashier['id']}/deactivate",
        headers=admin_headers(client),
        json={"reason": "پایان دسترسی فروش"},
    )
    assert deactivated.status_code == 200
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {fresh_token}"}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"username": "cashier", "password": "replacement-456"}).status_code == 401


def test_self_deactivate_and_admin_reset_are_blocked(client: TestClient) -> None:
    headers = admin_headers(client)
    admin_id = client.get("/api/v1/auth/me", headers=headers).json()["id"]
    deactivate = client.post(
        f"/api/v1/users/{admin_id}/deactivate",
        headers=headers,
        json={"reason": "نباید مجاز باشد"},
    )
    reset = client.post(
        f"/api/v1/users/{admin_id}/reset-password",
        headers=headers,
        json={"temporary_password": "another-admin-123", "reason": "نباید مجاز باشد"},
    )
    assert deactivate.status_code == 409
    assert reset.status_code == 409
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200


def test_superuser_accounts_cannot_be_mutated_through_subadmin_endpoints(
    client: TestClient, db_session: Session
) -> None:
    second_admin = User(
        username="second-admin",
        full_name="مدیر اصلی دوم",
        hashed_password=get_password_hash("second-admin-123"),
        is_active=True,
        is_superuser=True,
    )
    db_session.add(second_admin)
    db_session.commit()
    headers = admin_headers(client)
    deactivate = client.post(
        f"/api/v1/users/{second_admin.id}/deactivate",
        headers=headers,
        json={"reason": "این مسیر نباید مدیر اصلی را تغییر دهد"},
    )
    reset = client.post(
        f"/api/v1/users/{second_admin.id}/reset-password",
        headers=headers,
        json={"temporary_password": "replacement-admin-456", "reason": "این مسیر مخصوص زیرمدیر است"},
    )
    assert deactivate.status_code == 409
    assert reset.status_code == 409
    db_session.refresh(second_admin)
    assert second_admin.is_active is True


def test_admin_audits_have_safe_before_after_snapshots(client: TestClient, db_session: Session) -> None:
    cashier = create_cashier(client, can_catalog_inventory=True)
    headers = admin_headers(client)
    client.patch(
        f"/api/v1/users/{cashier['id']}",
        headers=headers,
        json={"full_name": "صندوقدار عصر", "can_sales": False, "can_catalog_inventory": False, "reason": "تغییر شیفت و دسترسی"},
    )
    client.post(
        f"/api/v1/users/{cashier['id']}/reset-password",
        headers=headers,
        json={"temporary_password": "audit-pass-789", "reason": "بازنشانی آزمایشی"},
    )
    audits = list(db_session.scalars(select(UserAdminAudit).where(UserAdminAudit.target_user_id == cashier["id"]).order_by(UserAdminAudit.id)))
    assert [audit.action for audit in audits] == ["create", "update", "reset_password"]
    assert audits[0].before_json is None
    assert audits[0].after_json["username"] == "cashier"
    assert audits[1].before_json["can_sales"] is True
    assert audits[1].after_json["can_sales"] is False
    assert audits[1].before_json["can_catalog_inventory"] is True
    assert audits[1].after_json["can_catalog_inventory"] is False
    encoded = json.dumps([audit.before_json for audit in audits] + [audit.after_json for audit in audits])
    assert "password" not in encoded.lower()
    assert "hash" not in encoded.lower()
    assert "token_version" not in encoded
    assert all(audit.reason for audit in audits)


def test_ledger_operator_can_manage_ledger_with_actor_audit_but_not_cheques_or_reports(
    client: TestClient, db_session: Session
) -> None:
    operator = create_cashier(
        client,
        username="ledger",
        password="ledger-pass-123",
        can_sales=False,
        can_ledger=True,
    )
    headers = {"Authorization": f"Bearer {login(client, 'ledger', 'ledger-pass-123')}"}
    person = client.post(
        "/api/v1/persons",
        headers=headers,
        json={"name": "مشتری دفتر", "person_type": "customer", "credit_status": "normal"},
    )
    assert person.status_code == 201, person.text
    person_id = person.json()["id"]
    entry = client.post(
        "/api/v1/ledger/manual-entry",
        headers=headers,
        json={"person_id": person_id, "entry_type": "debit", "amount_rial": 900000, "source_type": "manual", "jalali_date": "1405/06/18", "due_jalali_date": "1405/06/25", "local_time": "10:00", "description": "نسیه آزمایشی"},
    )
    assert entry.status_code == 201, entry.text
    settlement = client.post(
        "/api/v1/settlements",
        headers=headers,
        json={"person_id": person_id, "entry_type": "debit", "amount_rial": 100000, "jalali_date": "1405/06/19", "local_time": "11:00", "note": "دریافت بخشی"},
    )
    assert settlement.status_code == 201, settlement.text
    assert client.get(f"/api/v1/ledger/persons/{person_id}", headers=headers).status_code == 200
    assert client.get("/api/v1/due-reminders?today_jalali=1405/06/20&through_jalali=1405/06/30", headers=headers).status_code == 200
    assert client.get("/api/v1/cheques", headers=headers).status_code == 403
    assert client.get("/api/v1/reports/customer-debts", headers=headers).status_code == 403

    audits = list(db_session.scalars(select(LedgerActionAudit).order_by(LedgerActionAudit.id)))
    assert [(item.entity_type, item.action) for item in audits] == [
        ("person", "create"),
        ("ledger_entry", "create"),
        ("settlement", "create"),
    ]
    assert all(item.actor_user_id == operator["id"] for item in audits)
    assert all(item.actor_username == "ledger" for item in audits)

    old_token = login(client, "ledger", "ledger-pass-123")
    update = client.patch(
        f"/api/v1/users/{operator['id']}",
        headers=admin_headers(client),
        json={"can_ledger": False, "reason": "پایان مسئولیت دفتر"},
    )
    assert update.status_code == 200
    assert client.get("/api/v1/persons", headers={"Authorization": f"Bearer {old_token}"}).status_code == 401


def test_sales_customer_summary_is_minimal_and_does_not_leak_without_sales_permission(
    client: TestClient, db_session: Session
) -> None:
    sales_user = create_cashier(client, username="sales-summary", password="sales-pass-123", can_sales=True)
    ledger_user = create_cashier(
        client,
        username="ledger-summary",
        password="ledger-pass-456",
        can_sales=False,
        can_ledger=True,
    )
    customer = Person(name="مشتری خلاصه", person_type="customer", is_active=True)
    supplier = Person(name="تأمین‌کننده خلاصه", person_type="supplier", is_active=True)
    inactive = Person(name="مشتری غیرفعال", person_type="customer", is_active=False)
    db_session.add_all([customer, supplier, inactive])
    db_session.flush()
    db_session.add(
        LedgerEntry(
            person_id=customer.id,
            entry_type="debit",
            amount_rial=700_000,
            remaining_rial=700_000,
            source_type="manual",
            jalali_date="1405/06/20",
            local_time="10:00",
            description="جزئیات محرمانه گردش",
        )
    )
    db_session.commit()
    sales_headers = {"Authorization": f"Bearer {login(client, 'sales-summary', 'sales-pass-123')}"}
    ledger_headers = {"Authorization": f"Bearer {login(client, 'ledger-summary', 'ledger-pass-456')}"}

    response = client.get(f"/api/v1/sales/customers/{customer.id}/account-summary", headers=sales_headers)
    assert response.status_code == 200
    assert response.json() == {
        "person_id": customer.id,
        "debit_open_rial": 700_000,
        "credit_open_rial": 0,
        "net_balance_rial": 700_000,
        "open_entries_count": 1,
    }
    assert "description" not in response.text and "محرمانه" not in response.text
    assert client.get(
        f"/api/v1/sales/customers/{customer.id}/account-summary", headers=ledger_headers
    ).status_code == 403
    assert client.get(
        f"/api/v1/sales/customers/{supplier.id}/account-summary", headers=sales_headers
    ).status_code == 404
    assert client.get(
        f"/api/v1/sales/customers/{inactive.id}/account-summary", headers=sales_headers
    ).status_code == 404
    assert sales_user["id"] != ledger_user["id"]


def test_cheque_report_operator_is_audited_and_cannot_cancel(client: TestClient, db_session: Session) -> None:
    operator = create_cashier(
        client,
        username="cheques",
        password="cheques-pass-123",
        can_sales=False,
        can_cheques_reports=True,
    )
    headers = {"Authorization": f"Bearer {login(client, 'cheques', 'cheques-pass-123')}"}
    assert client.get("/api/v1/cheques/form-options", headers=headers).status_code == 200
    created = client.post(
        "/api/v1/cheques",
        headers=headers,
        json={
            "cheque_type": "received",
            "bank_name": "ملی",
            "cheque_number": "۱۲۳۴۵",
            "amount_rial": 500000,
            "issue_jalali_date": "1405/06/20",
            "due_jalali_date": "1405/06/25",
            "local_time": "10:00",
        },
    )
    assert created.status_code == 201, created.text
    cheque_id = created.json()["id"]
    assert client.get("/api/v1/cheques", headers=headers).status_code == 200
    assert client.get("/api/v1/reports/customer-debts", headers=headers).status_code == 200
    reminders = client.get(
        "/api/v1/due-reminders?today_jalali=1405/06/20&through_jalali=1405/06/30", headers=headers
    )
    assert reminders.status_code == 200
    assert {item["kind"] for item in reminders.json()["upcoming"]["items"]} == {"cheque"}
    canceled = client.post(
        f"/api/v1/cheques/{cheque_id}/events",
        headers=headers,
        json={"event_type": "canceled", "jalali_date": "1405/06/21", "local_time": "11:00"},
    )
    assert canceled.status_code == 403
    assert db_session.get(Cheque, cheque_id).status == "pending"
    audits = list(db_session.scalars(select(ChequeAudit).where(ChequeAudit.cheque_id == cheque_id)))
    assert len(audits) == 1
    assert audits[0].actor_user_id == operator["id"]

    old_token = login(client, "cheques", "cheques-pass-123")
    response = client.patch(
        f"/api/v1/users/{operator['id']}",
        headers=admin_headers(client),
        json={"can_cheques_reports": False, "reason": "پایان مسئولیت چک"},
    )
    assert response.status_code == 200
    assert client.get("/api/v1/cheques", headers={"Authorization": f"Bearer {old_token}"}).status_code == 401


def test_0016_migration_preserves_legacy_users_with_deny_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "legacy-users.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "0015_cheque_audits")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO users
                    (username, full_name, hashed_password, is_active, is_superuser, token_version, created_at_utc)
                VALUES
                    ('legacy', 'کاربر قدیمی', 'not-a-real-hash', 1, 0, 0, CURRENT_TIMESTAMP)
                """
            )
        )
    command.upgrade(config, "head")
    with engine.connect() as connection:
        legacy = connection.execute(text("SELECT * FROM users WHERE username='legacy'")).mappings().one()
        columns = {column["name"] for column in inspect(connection).get_columns("user_admin_audits")}
        integrity = connection.execute(text("PRAGMA integrity_check")).scalar_one()
    assert integrity == "ok"
    assert legacy["can_sales"] == 0
    assert legacy["can_catalog_inventory"] == 0
    assert legacy["can_ledger"] == 0
    assert legacy["can_cheques_reports"] == 0
    assert {"actor_user_id", "target_user_id", "before_json", "after_json", "reason"} <= columns
    get_settings.cache_clear()
