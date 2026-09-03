from collections.abc import Generator
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash
from app.core.time import current_jalali_date
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.catalog import Category, Product, ProductVariant, Unit
from app.models.purchases import InventoryItem
from app.models.user import User
from app.services import online as online_service

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
ONLINE_TOKEN = "online-token-123456"


@pytest.fixture(autouse=True)
def fixed_current_jalali_date(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(online_service, "current_jalali_date", lambda: "1405/07/01")


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
        variant = ProductVariant(
            product=product,
            unit=unit,
            name="Tarem Rice",
            sku="RICE-TAREM",
            retail_price_rial=1_250_000,
        )
        db.add_all([user, unit, category, product, variant])
        db.flush()
        db.add(InventoryItem(variant_id=variant.id, quantity_on_hand=Decimal("10"), weighted_average_cost_rial=900_000))
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


def create_channel(client: TestClient, auth_headers: dict[str, str]) -> dict:
    response = client.post(
        "/api/v1/online/channels",
        json={"name": "Website", "token": ONLINE_TOKEN},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert "token" not in response.json()
    assert "token_hash" not in response.json()
    return response.json()


def test_online_catalog_uses_token_and_online_price_rule(client: TestClient, auth_headers: dict[str, str]) -> None:
    channel = create_channel(client, auth_headers)
    rule = client.post(
        "/api/v1/online/price-rules",
        json={"channel_id": channel["id"], "variant_id": 1, "price_rial": 1_180_000, "min_quantity": "1"},
        headers=auth_headers,
    )
    assert rule.status_code == 201

    unauthorized = client.get("/api/v1/online/public/catalog", headers={"X-Online-Token": "wrong-token"})
    catalog = client.get("/api/v1/online/public/catalog", headers={"X-Online-Token": ONLINE_TOKEN})

    assert unauthorized.status_code == 401
    assert catalog.status_code == 200
    assert catalog.json()[0]["online_price_rial"] == 1_180_000
    assert Decimal(catalog.json()[0]["available_quantity"]) == Decimal("10.000")


def test_public_online_order_creates_order_and_stock_reservation(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    create_channel(client, auth_headers)
    response = client.post(
        "/api/v1/online/public/orders",
        json={
            "external_order_id": "WEB-1001",
            "customer_name": "Customer One",
            "customer_phone": "09120000000",
            "discount_amount_rial": 100_000,
            "jalali_date": "1405/07/01",
            "local_time": "12:10",
            "items": [{"variant_id": 1, "quantity": "2"}],
        },
        headers={"X-Online-Token": ONLINE_TOKEN},
    )
    orders = client.get("/api/v1/online/orders", headers=auth_headers)
    catalog = client.get("/api/v1/online/public/catalog", headers={"X-Online-Token": ONLINE_TOKEN})

    assert response.status_code == 201
    assert response.json()["subtotal_rial"] == 2_500_000
    assert response.json()["total_rial"] == 2_400_000
    assert response.json()["items"][0]["product_snapshot"] == "Tarem Rice"
    assert orders.status_code == 200
    assert orders.json()[0]["external_order_id"] == "WEB-1001"
    assert Decimal(catalog.json()[0]["available_quantity"]) == Decimal("8.000")


def test_online_order_rejects_duplicate_external_order_and_insufficient_stock(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    create_channel(client, auth_headers)
    payload = {
        "external_order_id": "WEB-1002",
        "jalali_date": "1405/07/01",
        "local_time": "12:10",
        "items": [{"variant_id": 1, "quantity": "1"}],
    }
    created = client.post("/api/v1/online/public/orders", json=payload, headers={"X-Online-Token": ONLINE_TOKEN})
    duplicate = client.post("/api/v1/online/public/orders", json=payload, headers={"X-Online-Token": ONLINE_TOKEN})
    overstock = client.post(
        "/api/v1/online/public/orders",
        json={**payload, "external_order_id": "WEB-1003", "items": [{"variant_id": 1, "quantity": "20"}]},
        headers={"X-Online-Token": ONLINE_TOKEN},
    )

    assert created.status_code == 201
    assert duplicate.status_code == 409
    assert overstock.status_code == 409


def test_online_order_aggregates_repeated_variant_before_stock_check(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    create_channel(client, auth_headers)
    response = client.post(
        "/api/v1/online/public/orders",
        json={
            "external_order_id": "WEB-1004",
            "jalali_date": "1405/07/01",
            "local_time": "12:10",
            "items": [
                {"variant_id": 1, "quantity": "6"},
                {"variant_id": 1, "quantity": "6"},
            ],
        },
        headers={"X-Online-Token": ONLINE_TOKEN},
    )

    assert response.status_code == 409


def test_admin_stock_reservation_requires_available_stock(client: TestClient, auth_headers: dict[str, str]) -> None:
    channel = create_channel(client, auth_headers)
    ok = client.post(
        "/api/v1/online/reservations",
        json={
            "channel_id": channel["id"],
            "variant_id": 1,
            "quantity": "3",
            "expires_jalali_date": "1405/07/02",
            "local_time": "13:00",
        },
        headers=auth_headers,
    )
    too_much = client.post(
        "/api/v1/online/reservations",
        json={
            "channel_id": channel["id"],
            "variant_id": 1,
            "quantity": "8",
            "expires_jalali_date": "1405/07/02",
            "local_time": "13:00",
        },
        headers=auth_headers,
    )

    assert ok.status_code == 201
    assert ok.json()["status"] == "reserved"
    assert too_much.status_code == 409


def test_admin_lists_price_rules_and_reservations_with_filters(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    channel = create_channel(client, auth_headers)
    created_rule = client.post(
        "/api/v1/online/price-rules",
        json={"channel_id": channel["id"], "variant_id": 1, "price_rial": 1_100_000, "min_quantity": "2"},
        headers=auth_headers,
    )
    created_reservation = client.post(
        "/api/v1/online/reservations",
        json={
            "channel_id": channel["id"],
            "variant_id": 1,
            "quantity": "2",
            "expires_jalali_date": "1405/07/02",
            "local_time": "14:00",
        },
        headers=auth_headers,
    )

    rules = client.get(f"/api/v1/online/price-rules?channel_id={channel['id']}", headers=auth_headers)
    reservations = client.get(
        f"/api/v1/online/reservations?channel_id={channel['id']}&status=reserved&as_of_jalali_date=1405/07/01",
        headers=auth_headers,
    )

    assert created_rule.status_code == 201
    assert created_reservation.status_code == 201
    assert rules.status_code == 200
    assert rules.json()[0]["price_rial"] == 1_100_000
    assert reservations.status_code == 200
    assert reservations.json()[0]["is_expired"] is False


def test_expired_reservation_does_not_reduce_available_stock_at_effective_date(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channel = create_channel(client, auth_headers)
    reservation = client.post(
        "/api/v1/online/reservations",
        json={
            "channel_id": channel["id"],
            "variant_id": 1,
            "quantity": "8",
            "expires_jalali_date": "1405/07/02",
            "local_time": "13:00",
        },
        headers=auth_headers,
    )
    monkeypatch.setattr(online_service, "current_jalali_date", lambda: "1405/07/02")
    before_expiry = client.get("/api/v1/online/public/catalog", headers={"X-Online-Token": ONLINE_TOKEN})
    monkeypatch.setattr(online_service, "current_jalali_date", lambda: "1405/07/03")
    after_expiry = client.get("/api/v1/online/public/catalog", headers={"X-Online-Token": ONLINE_TOKEN})
    listed = client.get(
        "/api/v1/online/reservations?as_of_jalali_date=1405/07/03",
        headers=auth_headers,
    )

    assert reservation.status_code == 201
    assert Decimal(before_expiry.json()[0]["available_quantity"]) == Decimal("2.000")
    assert Decimal(after_expiry.json()[0]["available_quantity"]) == Decimal("10.000")
    assert listed.json()[0]["is_expired"] is True


def test_reservation_rejects_expiry_before_effective_date(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    channel = create_channel(client, auth_headers)
    response = client.post(
        "/api/v1/online/reservations",
        json={
            "channel_id": channel["id"],
            "variant_id": 1,
            "quantity": "1",
            "expires_jalali_date": "1405/06/30",
            "local_time": "13:00",
        },
        headers=auth_headers,
    )

    assert response.status_code == 422
    assert "تاریخ موثر" in response.json()["detail"]


def test_current_jalali_date_works_without_platform_tzdata() -> None:
    assert current_jalali_date(datetime(2026, 9, 3, tzinfo=timezone.utc)) == "1405/06/12"


def test_channel_rejects_blank_name_and_whitespace_token(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/online/channels",
        json={"name": "   ", "token": "                "},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_online_price_rule_requires_positive_price(client: TestClient, auth_headers: dict[str, str]) -> None:
    channel = create_channel(client, auth_headers)
    response = client.post(
        "/api/v1/online/price-rules",
        json={"channel_id": channel["id"], "variant_id": 1, "price_rial": 0},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_future_order_date_cannot_bypass_current_active_reservation(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    channel = create_channel(client, auth_headers)
    reservation = client.post(
        "/api/v1/online/reservations",
        json={
            "channel_id": channel["id"],
            "variant_id": 1,
            "quantity": "10",
            "expires_jalali_date": "1405/07/10",
            "local_time": "13:00",
        },
        headers=auth_headers,
    )
    order = client.post(
        "/api/v1/online/public/orders",
        json={
            "external_order_id": "FUTURE-BYPASS",
            "jalali_date": "1405/08/01",
            "local_time": "13:05",
            "items": [{"variant_id": 1, "quantity": "1"}],
        },
        headers={"X-Online-Token": ONLINE_TOKEN},
    )

    assert reservation.status_code == 201
    assert order.status_code == 409


def test_admin_online_list_endpoints_require_login(client: TestClient) -> None:
    assert client.get("/api/v1/online/price-rules").status_code == 401
    assert client.get("/api/v1/online/reservations").status_code == 401
