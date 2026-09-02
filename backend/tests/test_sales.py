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
from app.models.catalog import Category, Product, ProductVariant, Unit
from app.models.purchases import InventoryItem, InventoryTransaction
from app.models.sales import SaleInvoice, SaleInvoiceItem
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
