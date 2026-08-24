from collections.abc import Generator
from decimal import Decimal

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
from app.models.purchases import InventoryItem
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
        product = Product(name="Rice", category=category)
        variant = ProductVariant(product=product, unit=unit, name="Tarem Rice", retail_price_rial=1250000)
        db.add_all([user, unit, category, product, variant])
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


def purchase_payload(quantity: str = "100", unit_cost: int = 900000) -> dict:
    return {
        "supplier_name": "Supplier One",
        "jalali_date": "1405/06/01",
        "local_time": "10:15",
        "discount_amount_rial": 0,
        "extra_cost_rial": 0,
        "paid_total_rial": 20000000,
        "items": [{"variant_id": 1, "quantity": quantity, "unit_cost_rial": unit_cost}],
    }


def test_create_purchase_creates_inventory_lot_and_transaction(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post("/api/v1/purchase-invoices", json=purchase_payload(), headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["invoice_number"] == "P-000001"
    assert data["subtotal_rial"] == 90000000
    assert data["total_rial"] == 90000000
    assert data["paid_total_rial"] == 20000000
    assert data["due_total_rial"] == 70000000
    assert data["items"][0]["line_total_rial"] == 90000000

    inventory = client.get("/api/v1/inventory", headers=auth_headers)
    assert inventory.status_code == 200
    row = inventory.json()[0]
    assert row["variant_name"] == "Tarem Rice"
    assert Decimal(row["quantity_on_hand"]) == Decimal("100.000")
    assert row["weighted_average_cost_rial"] == 900000


def test_second_purchase_recalculates_weighted_average(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.post("/api/v1/purchase-invoices", json=purchase_payload("100", 900000), headers=auth_headers)
    client.post("/api/v1/purchase-invoices", json=purchase_payload("100", 1100000), headers=auth_headers)

    inventory = client.get("/api/v1/inventory", headers=auth_headers).json()[0]

    assert Decimal(inventory["quantity_on_hand"]) == Decimal("200.000")
    assert inventory["weighted_average_cost_rial"] == 1000000


def test_cancel_purchase_reverses_inventory(client: TestClient, auth_headers: dict[str, str]) -> None:
    created = client.post("/api/v1/purchase-invoices", json=purchase_payload("100", 900000), headers=auth_headers)
    invoice_id = created.json()["id"]

    canceled = client.post(f"/api/v1/purchase-invoices/{invoice_id}/cancel", headers=auth_headers)
    inventory = client.get("/api/v1/inventory", headers=auth_headers).json()[0]

    assert canceled.status_code == 200
    assert canceled.json()["status"] == "canceled"
    assert canceled.json()["is_active"] is False
    assert Decimal(inventory["quantity_on_hand"]) == Decimal("0.000")
    assert inventory["weighted_average_cost_rial"] == 0


def test_cancel_purchase_fails_when_stock_is_insufficient(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
) -> None:
    created = client.post("/api/v1/purchase-invoices", json=purchase_payload("100", 900000), headers=auth_headers)
    invoice_id = created.json()["id"]
    inventory = db_session.query(InventoryItem).filter(InventoryItem.variant_id == 1).one()
    inventory.quantity_on_hand = Decimal("50")
    db_session.commit()

    canceled = client.post(f"/api/v1/purchase-invoices/{invoice_id}/cancel", headers=auth_headers)

    assert canceled.status_code == 409
    assert canceled.json()["detail"] == "موجودی برای لغو این خرید کافی نیست."


def test_bad_purchase_payload_is_rejected(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/purchase-invoices",
        json={
            "jalali_date": "2026-08-24",
            "local_time": "25:00",
            "items": [],
        },
        headers=auth_headers,
    )

    assert response.status_code == 422
