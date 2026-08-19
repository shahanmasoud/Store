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


@pytest.fixture()
def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_catalog_flow_creates_core_records(client: TestClient, auth_headers: dict[str, str]) -> None:
    unit = client.post("/api/v1/units", json={"name": "کیلوگرم", "symbol": "kg"}, headers=auth_headers)
    assert unit.status_code == 201
    unit_id = unit.json()["id"]

    category = client.post("/api/v1/categories", json={"name": "برنج"}, headers=auth_headers)
    assert category.status_code == 201
    category_id = category.json()["id"]

    product = client.post(
        "/api/v1/products",
        json={"name": "برنج", "description": "کالای پایه برنج", "category_id": category_id},
        headers=auth_headers,
    )
    assert product.status_code == 201
    product_id = product.json()["id"]

    variant = client.post(
        "/api/v1/product-variants",
        json={
            "product_id": product_id,
            "unit_id": unit_id,
            "name": "برنج ایرانی طارم",
            "sku": "RICE-TAREM-IR",
            "retail_price_rial": 1250000,
            "wholesale_price_rial": 1180000,
            "min_wholesale_quantity": "50",
        },
        headers=auth_headers,
    )
    assert variant.status_code == 201
    variant_id = variant.json()["id"]

    price = client.post(
        "/api/v1/prices",
        json={
            "variant_id": variant_id,
            "price_type": "retail",
            "amount_rial": 1250000,
            "jalali_date": "1405/05/29",
            "local_time": "09:30",
        },
        headers=auth_headers,
    )
    assert price.status_code == 201
    assert price.json()["timezone"] == "Asia/Tehran"


def test_catalog_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/products")

    assert response.status_code == 401


def test_price_rejects_bad_jalali_date(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/prices",
        json={
            "variant_id": 1,
            "price_type": "retail",
            "amount_rial": 1250000,
            "jalali_date": "2026-08-20",
            "local_time": "09:30",
        },
        headers=auth_headers,
    )

    assert response.status_code == 422
