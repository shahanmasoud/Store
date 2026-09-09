from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.catalog import Category, Product, ProductVariant, Unit
from app.models.purchases import InventoryItem, InventoryTransaction
from app.models.ledger import Person
from app.models.ledger import LedgerEntry
from app.models.sales import Payment, PaymentDueAudit, SaleInvoice, SaleInvoiceItem
from app.models.user import User
from app.core.time import utc_now
from app.schemas.sales import PaymentDueDateUpdate
from app.services.sales import update_payment_due_date

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
        user = User(
            username="admin",
            full_name="System Admin",
            hashed_password=get_password_hash("admin123"),
            is_active=True,
            is_superuser=True,
        )
        unit = Unit(name="Kilogram", symbol="kg")
        category = Category(name="Rice")
        product = Product(name="Tarem Rice", category=category)
        variant = ProductVariant(product=product, unit=unit, name="Tarem 10kg", retail_price_rial=1250000)
        db.add_all([user, unit, category, product, variant])
        db.flush()
        db.add(InventoryItem(variant_id=variant.id, quantity_on_hand=10, weighted_average_cost_rial=750000))
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
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def sale_payload() -> dict:
    return {
        "customer_name": "Walk-in customer",
        "jalali_date": "1405/05/29",
        "local_time": "09:30",
        "discount_amount_rial": 50000,
        "items": [
            {
                "variant_id": 1,
                "quantity": "2",
                "unit_price_rial": 1000000,
                "discount_amount_rial": 100000,
                "estimated_cost_rial": 1500000,
            }
        ],
        "payments": [
            {"method": "cash", "amount_rial": 1000000},
            {"method": "credit", "amount_rial": 850000},
        ],
    }


def test_create_sale_calculates_totals_and_default_payment_statuses(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
) -> None:
    response = client.post("/api/v1/sales", json=sale_payload(), headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["subtotal_rial"] == 1900000
    assert data["discount_amount_rial"] == 50000
    assert data["total_rial"] == 1850000
    assert data["paid_total_rial"] == 1000000
    assert data["due_total_rial"] == 850000
    assert data["customer_id"] is None
    assert data["customer_name"] == "Walk-in customer"
    assert data["status"] == "active"
    assert data["is_active"] is True
    assert data["items"][0]["discount_amount_rial"] == 100000
    assert data["items"][0]["line_total_rial"] == 1900000
    assert data["items"][0]["estimated_cost_rial"] == 1500000
    assert data["items"][0]["estimated_profit_rial"] == 400000
    assert data["payments"][0]["status"] == "received"
    assert data["payments"][1]["status"] == "pending"
    inventory = db_session.get(InventoryItem, 1)
    assert inventory is not None
    assert str(inventory.quantity_on_hand) == "8.000"
    transaction = db_session.query(InventoryTransaction).filter_by(transaction_type="sale_out").one()
    assert str(transaction.quantity_delta) == "-2.000"
    assert transaction.sale_invoice_id == data["id"]
    assert transaction.sale_invoice_item_id == data["items"][0]["id"]


def test_sale_endpoint_accepts_localized_money_quantity_date_and_reference(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    payload = sale_payload()
    payload["jalali_date"] = "۱۴۰۵/۰۵/۲۹"
    payload["local_time"] = "۰۹:۳۰"
    payload["discount_amount_rial"] = "۵۰٬۰۰۰"
    payload["items"][0] |= {"quantity": "۲٫۰", "unit_price_rial": "۱٬۰۰۰٬۰۰۰", "discount_amount_rial": "۱۰۰٬۰۰۰"}
    payload["payments"] = [{"method": "cash", "amount_rial": "۱٬۸۵۰٬۰۰۰", "reference_number": " ۱۲٣-۴۵۶ "}]

    response = client.post("/api/v1/sales", json=payload, headers=auth_headers)

    assert response.status_code == 201
    assert response.json()["total_rial"] == 1_850_000
    assert response.json()["jalali_date"] == "1405/05/29"
    assert response.json()["payments"][0]["reference_number"] == "123-456"


def test_create_sale_links_active_customer_and_uses_canonical_name_snapshot(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
) -> None:
    customer = Person(name="مشتری اصلی", phone="09120000000", person_type="customer")
    db_session.add(customer)
    db_session.commit()
    payload = sale_payload() | {"customer_id": customer.id, "customer_name": "نام اشتباه ارسالی"}

    response = client.post("/api/v1/sales", json=payload, headers=auth_headers)

    assert response.status_code == 201
    assert response.json()["customer_id"] == customer.id
    assert response.json()["customer_name"] == "مشتری اصلی"
    invoice = db_session.get(SaleInvoice, response.json()["id"])
    assert invoice is not None
    assert invoice.customer_id == customer.id
    assert invoice.customer_name == "مشتری اصلی"
    customer.name = "نام جدید مشتری"
    db_session.commit()
    fetched = client.get(f"/api/v1/sales/{invoice.id}", headers=auth_headers)
    listed = client.get("/api/v1/sales", headers=auth_headers)
    assert fetched.status_code == 200
    assert fetched.json()["customer_id"] == customer.id
    assert fetched.json()["customer_name"] == "مشتری اصلی"
    assert listed.json()[0]["customer_id"] == customer.id
    assert listed.json()[0]["customer_name"] == "مشتری اصلی"


def test_create_sale_rejects_supplier_only_person(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
) -> None:
    supplier = Person(name="فقط تأمین‌کننده", person_type="supplier")
    db_session.add(supplier)
    db_session.commit()

    response = client.post(
        "/api/v1/sales", json=sale_payload() | {"customer_id": supplier.id}, headers=auth_headers
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "شخص انتخاب‌شده مشتری نیست و نمی‌تواند به فاکتور فروش متصل شود."
    assert db_session.query(SaleInvoice).count() == 0


def test_create_sale_rejects_inactive_customer(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
) -> None:
    customer = Person(name="مشتری غیرفعال", person_type="customer", is_active=False)
    db_session.add(customer)
    db_session.commit()

    response = client.post(
        "/api/v1/sales", json=sale_payload() | {"customer_id": customer.id}, headers=auth_headers
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "مشتری فعال پیدا نشد."
    assert db_session.query(SaleInvoice).count() == 0


def test_daily_journal_separates_mixed_received_and_pending_payments(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    client.post("/api/v1/sales", json=sale_payload(), headers=auth_headers)

    response = client.get("/api/v1/daily-journal?jalali_date=1405/05/29", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["invoice_count"] == 1
    assert data["sales_total_rial"] == 1850000
    assert data["received_total_rial"] == 1000000
    assert data["pending_total_rial"] == 850000
    assert data["estimated_profit_rial"] == 350000
    by_method = {item["method"]: item for item in data["payments"]}
    assert by_method["cash"]["received_rial"] == 1000000
    assert by_method["credit"]["pending_rial"] == 850000


def test_cancel_sale_excludes_invoice_and_payments_from_daily_journal(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
) -> None:
    create_response = client.post("/api/v1/sales", json=sale_payload(), headers=auth_headers)
    invoice_id = create_response.json()["id"]

    cancel_response = client.post(f"/api/v1/sales/{invoice_id}/cancel", headers=auth_headers)
    journal_response = client.get("/api/v1/daily-journal?jalali_date=1405/05/29", headers=auth_headers)

    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "canceled"
    assert cancel_response.json()["is_active"] is False
    assert journal_response.status_code == 200
    assert journal_response.json()["invoice_count"] == 0
    assert journal_response.json()["sales_total_rial"] == 0
    assert journal_response.json()["received_total_rial"] == 0
    assert journal_response.json()["pending_total_rial"] == 0
    inventory = db_session.get(InventoryItem, 1)
    assert inventory is not None
    assert str(inventory.quantity_on_hand) == "10.000"
    assert db_session.query(InventoryTransaction).filter_by(transaction_type="cancel_sale").count() == 1

    second_cancel = client.post(f"/api/v1/sales/{invoice_id}/cancel", headers=auth_headers)
    db_session.refresh(inventory)
    assert second_cancel.status_code == 200
    assert str(inventory.quantity_on_hand) == "10.000"
    assert db_session.query(InventoryTransaction).filter_by(transaction_type="cancel_sale").count() == 1


def test_cancel_legacy_sale_without_linked_stock_out_does_not_inflate_inventory(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
) -> None:
    invoice = SaleInvoice(
        invoice_number="S-LEGACY",
        subtotal_rial=1_000_000,
        discount_amount_rial=0,
        total_rial=1_000_000,
        paid_total_rial=1_000_000,
        due_total_rial=0,
        jalali_date="1405/05/29",
        local_time="09:30",
    )
    db_session.add(invoice)
    db_session.flush()
    db_session.add(
        SaleInvoiceItem(
            invoice_id=invoice.id,
            variant_id=1,
            quantity=2,
            unit_price_rial=500_000,
            discount_amount_rial=0,
            line_total_rial=1_000_000,
            estimated_cost_rial=1_500_000,
            estimated_profit_rial=-500_000,
            product_snapshot="Tarem 10kg",
        )
    )
    db_session.commit()

    response = client.post(f"/api/v1/sales/{invoice.id}/cancel", headers=auth_headers)

    inventory = db_session.get(InventoryItem, 1)
    assert response.status_code == 200
    assert response.json()["status"] == "canceled"
    assert inventory is not None
    assert str(inventory.quantity_on_hand) == "10.000"
    assert db_session.query(InventoryTransaction).count() == 0


def test_sale_rejects_insufficient_inventory_without_partial_changes(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
) -> None:
    payload = sale_payload()
    payload["items"][0]["quantity"] = "11"

    response = client.post("/api/v1/sales", json=payload, headers=auth_headers)

    assert response.status_code == 409
    assert response.json()["detail"] == "موجودی کافی نیست: Tarem 10kg"
    inventory = db_session.get(InventoryItem, 1)
    assert inventory is not None
    assert str(inventory.quantity_on_hand) == "10.000"
    assert db_session.query(InventoryTransaction).count() == 0


def test_sale_rejects_mixed_payment_overassignment_without_changing_inventory(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
) -> None:
    payload = sale_payload()
    payload["payments"] = [
        {"method": "cash", "amount_rial": 1000000},
        {"method": "credit", "amount_rial": 900000},
    ]

    response = client.post("/api/v1/sales", json=payload, headers=auth_headers)

    assert response.status_code == 422
    assert response.json()["detail"] == "جمع پرداخت‌ها نمی‌تواند از مبلغ فاکتور بیشتر باشد."
    inventory = db_session.get(InventoryItem, 1)
    assert inventory is not None
    assert str(inventory.quantity_on_hand) == "10.000"


def test_bad_sale_payload_is_rejected(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/sales",
        json={
            "jalali_date": "2026-08-20",
            "local_time": "25:00",
            "items": [],
            "payments": [{"method": "cash", "amount_rial": 0}],
        },
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_daily_journal_rejects_bad_jalali_date(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/daily-journal?jalali_date=2026-08-20", headers=auth_headers)

    assert response.status_code == 422


def test_pending_sale_payment_due_date_set_change_clear_is_audited_without_ledger_changes(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
) -> None:
    created = client.post("/api/v1/sales", json=sale_payload(), headers=auth_headers).json()
    payment = next(item for item in created["payments"] if item["status"] == "pending")
    ledger_count = db_session.query(LedgerEntry).count()

    set_due = client.patch(
        f"/api/v1/sales/payments/{payment['id']}/due-date",
        json={
            "due_jalali_date": "۱۴۰۵/۰۶/۲۰",
            "reason": "  توافق با مشتری  ",
            "expected_updated_at": payment["updated_at_utc"],
        },
        headers=auth_headers,
    )
    assert set_due.status_code == 200
    assert set_due.json()["due_jalali_date"] == "1405/06/20"
    first_version = set_due.json()["updated_at_utc"]
    assert first_version != payment["updated_at_utc"]

    changed = client.patch(
        f"/api/v1/sales/payments/{payment['id']}/due-date",
        json={
            "due_jalali_date": "1405/06/25",
            "reason": "تمدید موعد",
            "expected_updated_at": first_version,
        },
        headers=auth_headers,
    )
    assert changed.status_code == 200
    cleared = client.patch(
        f"/api/v1/sales/payments/{payment['id']}/due-date",
        json={
            "due_jalali_date": None,
            "reason": "حذف موعد اشتباه",
            "expected_updated_at": changed.json()["updated_at_utc"],
        },
        headers=auth_headers,
    )
    assert cleared.status_code == 200
    assert cleared.json()["due_jalali_date"] is None

    audits = client.get(
        f"/api/v1/sales/payments/{payment['id']}/due-date/audits",
        headers=auth_headers,
    )
    assert audits.status_code == 200
    assert [item["before_due_date"] for item in audits.json()] == [None, "1405/06/20", "1405/06/25"]
    assert [item["after_due_date"] for item in audits.json()] == ["1405/06/20", "1405/06/25", None]
    assert [item["reason"] for item in audits.json()] == ["توافق با مشتری", "تمدید موعد", "حذف موعد اشتباه"]
    assert all(item["actor_username"] == "admin" for item in audits.json())
    assert db_session.query(PaymentDueAudit).count() == 3
    assert db_session.query(LedgerEntry).count() == ledger_count


def test_sale_payment_due_date_uses_optimistic_concurrency_and_rejects_noop(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
) -> None:
    created = client.post("/api/v1/sales", json=sale_payload(), headers=auth_headers).json()
    payment = next(item for item in created["payments"] if item["status"] == "pending")
    payload = {
        "due_jalali_date": "1405/06/20",
        "reason": "ثبت موعد",
        "expected_updated_at": payment["updated_at_utc"],
    }
    current = client.patch(
        f"/api/v1/sales/payments/{payment['id']}/due-date",
        json=payload,
        headers=auth_headers,
    )
    assert current.status_code == 200

    stale = client.patch(
        f"/api/v1/sales/payments/{payment['id']}/due-date",
        json={**payload, "due_jalali_date": "1405/06/21"},
        headers=auth_headers,
    )
    assert stale.status_code == 409
    assert "دوباره دریافت" in stale.json()["detail"]
    no_op = client.patch(
        f"/api/v1/sales/payments/{payment['id']}/due-date",
        json={**payload, "expected_updated_at": current.json()["updated_at_utc"]},
        headers=auth_headers,
    )
    assert no_op.status_code == 409
    assert db_session.query(PaymentDueAudit).count() == 1


def test_sale_payment_due_date_rejects_received_canceled_invalid_and_missing(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
) -> None:
    created = client.post("/api/v1/sales", json=sale_payload(), headers=auth_headers).json()
    received = next(item for item in created["payments"] if item["status"] == "received")
    pending = next(item for item in created["payments"] if item["status"] == "pending")

    received_response = client.patch(
        f"/api/v1/sales/payments/{received['id']}/due-date",
        json={"due_jalali_date": "1405/06/20", "reason": "نامعتبر", "expected_updated_at": received["updated_at_utc"]},
        headers=auth_headers,
    )
    assert received_response.status_code == 409
    assert client.post(f"/api/v1/sales/{created['id']}/cancel", headers=auth_headers).status_code == 200
    canceled_response = client.patch(
        f"/api/v1/sales/payments/{pending['id']}/due-date",
        json={"due_jalali_date": "1405/06/20", "reason": "نامعتبر", "expected_updated_at": pending["updated_at_utc"]},
        headers=auth_headers,
    )
    assert canceled_response.status_code == 409
    assert client.patch(
        "/api/v1/sales/payments/99999/due-date",
        json={"due_jalali_date": "1405/06/20", "reason": "ناموجود", "expected_updated_at": pending["updated_at_utc"]},
        headers=auth_headers,
    ).status_code == 404
    assert client.patch(
        f"/api/v1/sales/payments/{pending['id']}/due-date",
        json={"due_jalali_date": "1405/13/01", "reason": "نامعتبر", "expected_updated_at": pending["updated_at_utc"]},
        headers=auth_headers,
    ).status_code == 422
    assert db_session.query(PaymentDueAudit).count() == 0


def test_sale_payment_due_date_requires_sales_permission_and_records_subadmin_actor(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
) -> None:
    created = client.post("/api/v1/sales", json=sale_payload(), headers=auth_headers).json()
    payment = next(item for item in created["payments"] if item["status"] == "pending")
    assert client.patch(
        f"/api/v1/sales/payments/{payment['id']}/due-date",
        json={"due_jalali_date": "1405/06/20", "reason": "بدون نشست", "expected_updated_at": payment["updated_at_utc"]},
    ).status_code == 401

    from app.core.security import get_password_hash

    db_session.add_all([
        User(username="sales-due", full_name="مسئول فروش", hashed_password=get_password_hash("operator123"), is_active=True, is_superuser=False, can_sales=True),
        User(username="ledger-due", full_name="مسئول دفتر", hashed_password=get_password_hash("operator123"), is_active=True, is_superuser=False, can_ledger=True),
    ])
    db_session.commit()
    sales_token = client.post("/api/v1/auth/login", json={"username": "sales-due", "password": "operator123"}).json()["access_token"]
    ledger_token = client.post("/api/v1/auth/login", json={"username": "ledger-due", "password": "operator123"}).json()["access_token"]
    payload = {"due_jalali_date": "1405/06/20", "reason": "پیگیری فروش", "expected_updated_at": payment["updated_at_utc"]}
    assert client.patch(
        f"/api/v1/sales/payments/{payment['id']}/due-date",
        json=payload,
        headers={"Authorization": f"Bearer {ledger_token}"},
    ).status_code == 403
    updated = client.patch(
        f"/api/v1/sales/payments/{payment['id']}/due-date",
        json=payload,
        headers={"Authorization": f"Bearer {sales_token}"},
    )
    assert updated.status_code == 200
    audits = client.get(
        f"/api/v1/sales/payments/{payment['id']}/due-date/audits",
        headers={"Authorization": f"Bearer {sales_token}"},
    ).json()
    assert audits[0]["actor_username"] == "sales-due"
    assert audits[0]["actor_full_name"] == "مسئول فروش"
    assert client.get(
        f"/api/v1/sales/payments/{payment['id']}/due-date/audits",
        headers={"Authorization": f"Bearer {ledger_token}"},
    ).status_code == 403


def test_concurrent_sale_payment_due_updates_have_exactly_one_winner(tmp_path) -> None:
    database_path = tmp_path / "payment-due-race.db"
    engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    initial_version = utc_now()
    with SessionLocal() as setup:
        actor = User(
            username="race-sales",
            full_name="مسئول فروش هم‌زمان",
            hashed_password=get_password_hash("operator123"),
            is_active=True,
            is_superuser=False,
            can_sales=True,
        )
        invoice = SaleInvoice(
            invoice_number="S-RACE",
            subtotal_rial=1_000_000,
            discount_amount_rial=0,
            total_rial=1_000_000,
            paid_total_rial=0,
            due_total_rial=1_000_000,
            status="active",
            is_active=True,
            jalali_date="1405/06/01",
            local_time="10:00",
        )
        setup.add_all([actor, invoice])
        setup.flush()
        payment = Payment(
            invoice_id=invoice.id,
            method="credit",
            amount_rial=1_000_000,
            status="pending",
            jalali_date="1405/06/01",
            local_time="10:00",
            updated_at_utc=initial_version,
        )
        setup.add(payment)
        setup.commit()
        actor_id, payment_id = actor.id, payment.id

    ready = Barrier(2)

    def attempt(due_date: str) -> int:
        with SessionLocal() as db:
            # Keep the same original entity version in both identity maps. This
            # recreates the stale read that a read-then-write implementation misses.
            db.get(Payment, payment_id)
            actor = db.get(User, actor_id)
            assert actor is not None
            ready.wait()
            try:
                update_payment_due_date(
                    db,
                    payment_id,
                    PaymentDueDateUpdate(
                        due_jalali_date=due_date,
                        reason=f"رقابت برای {due_date}",
                        expected_updated_at=initial_version,
                    ),
                    actor,
                )
                return 200
            except HTTPException as exc:
                return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(attempt, ["1405/06/20", "1405/06/21"]))

    assert sorted(statuses) == [200, 409]
    with SessionLocal() as verify:
        assert verify.query(PaymentDueAudit).count() == 1
        assert verify.get(Payment, payment_id).due_jalali_date in {"1405/06/20", "1405/06/21"}
    engine.dispose()
