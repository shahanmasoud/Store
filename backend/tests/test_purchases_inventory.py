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
from app.models.purchases import InventoryItem, InventoryTransaction
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
        second_variant = ProductVariant(product=product, unit=unit, name="Hashemi Rice", retail_price_rial=1350000)
        db.add_all([user, unit, category, product, variant, second_variant])
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


def purchase_payload(quantity: str = "100", unit_cost: int = 900000, variant_id: int = 1) -> dict:
    return {
        "supplier_name": "Supplier One",
        "jalali_date": "1405/06/01",
        "local_time": "10:15",
        "discount_amount_rial": 0,
        "extra_cost_rial": 0,
        "paid_total_rial": 20000000,
        "items": [{"variant_id": variant_id, "quantity": quantity, "unit_cost_rial": unit_cost}],
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


def test_inventory_reorder_level_can_be_set_and_cleared(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.post("/api/v1/purchase-invoices", json=purchase_payload(), headers=auth_headers)

    updated = client.patch("/api/v1/inventory/1", json={"reorder_level": "25.5"}, headers=auth_headers)
    cleared = client.patch("/api/v1/inventory/1", json={"reorder_level": None}, headers=auth_headers)

    assert updated.status_code == 200
    assert Decimal(updated.json()["reorder_level"]) == Decimal("25.500")
    assert cleared.status_code == 200
    assert cleared.json()["reorder_level"] is None


def test_inventory_reorder_level_validation_and_missing_row(client: TestClient, auth_headers: dict[str, str]) -> None:
    invalid = client.patch("/api/v1/inventory/1", json={"reorder_level": -1}, headers=auth_headers)
    missing_field = client.patch("/api/v1/inventory/1", json={}, headers=auth_headers)
    missing = client.patch("/api/v1/inventory/999", json={"reorder_level": 10}, headers=auth_headers)

    assert invalid.status_code == 422
    assert missing_field.status_code == 422
    assert missing.status_code == 404
    assert missing.json()["detail"] == "ردیف موجودی پیدا نشد."


def test_inventory_transactions_show_purchase_cancel_balance_and_filter(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    client.post("/api/v1/purchase-invoices", json=purchase_payload("10", 900000), headers=auth_headers)
    second = client.post("/api/v1/purchase-invoices", json=purchase_payload("5", 1100000), headers=auth_headers)
    client.post("/api/v1/purchase-invoices", json=purchase_payload("7", 1000000, 2), headers=auth_headers)
    client.post(f"/api/v1/purchase-invoices/{second.json()['id']}/cancel", headers=auth_headers)

    response = client.get("/api/v1/inventory-transactions?variant_id=1&limit=2", headers=auth_headers)

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 2
    assert all(row["variant_id"] == 1 for row in rows)
    assert rows[0]["transaction_type"] == "cancel_purchase"
    assert Decimal(rows[0]["quantity_delta"]) == Decimal("-5.000")
    assert Decimal(rows[0]["balance_after"]) == Decimal("10.000")
    assert rows[0]["variant_name"] == "Tarem Rice"
    assert rows[0]["purchase_invoice_id"] == second.json()["id"]
    assert rows[1]["transaction_type"] == "purchase_in"
    assert Decimal(rows[1]["balance_after"]) == Decimal("15.000")


def test_cancel_purchase_rejects_later_inventory_movement(client: TestClient, auth_headers: dict[str, str]) -> None:
    first = client.post("/api/v1/purchase-invoices", json=purchase_payload("10", 900000), headers=auth_headers)
    client.post("/api/v1/purchase-invoices", json=purchase_payload("5", 1100000), headers=auth_headers)

    canceled = client.post(f"/api/v1/purchase-invoices/{first.json()['id']}/cancel", headers=auth_headers)

    assert canceled.status_code == 409
    assert "پس از خرید گردش دیگری" in canceled.json()["detail"]
    inventory = client.get("/api/v1/inventory", headers=auth_headers).json()[0]
    assert Decimal(inventory["quantity_on_hand"]) == Decimal("15.000")


def test_cancel_purchase_checks_duplicate_variant_lines_as_a_total(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
) -> None:
    payload = purchase_payload("6", 900000)
    payload["items"].append({"variant_id": 1, "quantity": "6", "unit_cost_rial": 900000})
    created = client.post("/api/v1/purchase-invoices", json=payload, headers=auth_headers)
    inventory = db_session.query(InventoryItem).filter_by(variant_id=1).one()
    inventory.quantity_on_hand = Decimal("10")
    db_session.commit()

    canceled = client.post(f"/api/v1/purchase-invoices/{created.json()['id']}/cancel", headers=auth_headers)

    assert canceled.status_code == 409
    assert Decimal(inventory.quantity_on_hand) == Decimal("10")


def test_inventory_endpoints_require_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/inventory-transactions").status_code == 401
    assert client.patch("/api/v1/inventory/1", json={"reorder_level": 5}).status_code == 401


def test_inventory_transaction_limit_is_validated(client: TestClient, auth_headers: dict[str, str]) -> None:
    assert client.get("/api/v1/inventory-transactions?limit=0", headers=auth_headers).status_code == 422
    assert client.get("/api/v1/inventory-transactions?limit=201", headers=auth_headers).status_code == 422


def adjustment_payload(
    adjustment_type: str = "initial",
    quantity: str = "10",
    unit_cost_rial: int | None = 900000,
) -> dict:
    return {
        "variant_id": 1,
        "adjustment_type": adjustment_type,
        "quantity": quantity,
        "unit_cost_rial": unit_cost_rial,
        "reason": "شمارش اولیه انبار",
        "jalali_date": "1405/06/16",
        "local_time": "09:30",
    }


def test_superuser_can_record_initial_and_weighted_increase(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
) -> None:
    initial = client.post("/api/v1/inventory/adjustments", json=adjustment_payload(), headers=auth_headers)
    increase = client.post(
        "/api/v1/inventory/adjustments",
        json=adjustment_payload("increase", "10", 1100000),
        headers=auth_headers,
    )

    assert initial.status_code == 201
    assert initial.json()["transaction_type"] == "adjustment_initial"
    assert initial.json()["adjustment_type"] == "initial"
    assert initial.json()["reason"] == "شمارش اولیه انبار"
    assert initial.json()["actor_user_id"] == 1
    assert Decimal(initial.json()["balance_after"]) == Decimal("10.000")
    assert increase.status_code == 201
    inventory = db_session.query(InventoryItem).filter_by(variant_id=1).one()
    assert Decimal(inventory.quantity_on_hand) == Decimal("20.000")
    assert inventory.weighted_average_cost_rial == 1000000


def test_decrease_preserves_average_and_rejects_insufficient_stock_atomically(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
) -> None:
    client.post("/api/v1/inventory/adjustments", json=adjustment_payload(), headers=auth_headers)
    decreased = client.post(
        "/api/v1/inventory/adjustments",
        json=adjustment_payload("decrease", "4", None),
        headers=auth_headers,
    )
    rejected = client.post(
        "/api/v1/inventory/adjustments",
        json=adjustment_payload("decrease", "7", None),
        headers=auth_headers,
    )

    assert decreased.status_code == 201
    assert Decimal(decreased.json()["quantity_delta"]) == Decimal("-4.000")
    assert decreased.json()["unit_cost_rial"] == 900000
    assert rejected.status_code == 409
    inventory = db_session.query(InventoryItem).filter_by(variant_id=1).one()
    assert Decimal(inventory.quantity_on_hand) == Decimal("6.000")
    assert inventory.weighted_average_cost_rial == 900000
    assert db_session.query(InventoryTransaction).count() == 2


def test_initial_is_one_time_and_requires_no_prior_history(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
) -> None:
    first = client.post("/api/v1/inventory/adjustments", json=adjustment_payload(), headers=auth_headers)
    inventory = db_session.query(InventoryItem).filter_by(variant_id=1).one()
    inventory.quantity_on_hand = Decimal("0")
    db_session.commit()
    second = client.post("/api/v1/inventory/adjustments", json=adjustment_payload(), headers=auth_headers)

    assert first.status_code == 201
    assert second.status_code == 409
    assert db_session.query(InventoryTransaction).count() == 1


def test_adjustment_validation_and_history_are_auditable(client: TestClient, auth_headers: dict[str, str]) -> None:
    missing_cost = client.post(
        "/api/v1/inventory/adjustments",
        json=adjustment_payload("increase", "2", None),
        headers=auth_headers,
    )
    blank_reason_payload = adjustment_payload()
    blank_reason_payload["reason"] = "   "
    blank_reason = client.post("/api/v1/inventory/adjustments", json=blank_reason_payload, headers=auth_headers)
    localized = adjustment_payload(quantity="۱۲٫۵", unit_cost_rial=900000)
    created = client.post("/api/v1/inventory/adjustments", json=localized, headers=auth_headers)
    history = client.get("/api/v1/inventory-transactions?variant_id=1", headers=auth_headers)

    assert missing_cost.status_code == 422
    assert blank_reason.status_code == 422
    assert created.status_code == 201
    assert history.status_code == 200
    row = history.json()[0]
    assert row["adjustment_type"] == "initial"
    assert row["actor_user_id"] == 1
    assert row["reason"] == "شمارش اولیه انبار"


def test_adjustment_requires_superuser(client: TestClient, db_session: Session) -> None:
    clerk = User(
        username="clerk",
        full_name="Clerk",
        hashed_password=get_password_hash("clerk123"),
        is_active=True,
        is_superuser=False,
    )
    db_session.add(clerk)
    db_session.commit()
    login = client.post("/api/v1/auth/login", json={"username": "clerk", "password": "clerk123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.post("/api/v1/inventory/adjustments", json=adjustment_payload(), headers=headers)

    assert response.status_code == 403
    assert db_session.query(InventoryItem).count() == 0
    assert db_session.query(InventoryTransaction).count() == 0
