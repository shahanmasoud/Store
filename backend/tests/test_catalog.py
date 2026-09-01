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


def create_category(
    client: TestClient,
    auth_headers: dict[str, str],
    name: str,
    parent_id: int | None = None,
) -> dict:
    response = client.post(
        "/api/v1/categories",
        json={"name": name, "parent_id": parent_id},
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()


def test_category_hierarchy_can_be_created_and_listed(client: TestClient, auth_headers: dict[str, str]) -> None:
    parent = create_category(client, auth_headers, "  مواد غذایی  ")
    child = create_category(client, auth_headers, "برنج", parent["id"])

    response = client.get("/api/v1/categories", headers=auth_headers)

    assert response.status_code == 200
    assert parent["name"] == "مواد غذایی"
    assert child["parent_id"] == parent["id"]
    assert {item["name"] for item in response.json()} == {"مواد غذایی", "برنج"}


@pytest.mark.parametrize("parent_id", [9999, -1])
def test_category_rejects_missing_parent(
    client: TestClient,
    auth_headers: dict[str, str],
    parent_id: int,
) -> None:
    response = client.post(
        "/api/v1/categories",
        json={"name": "زیرمجموعه", "parent_id": parent_id},
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "دسته فعال پیدا نشد."


def test_category_update_changes_name_and_parent(client: TestClient, auth_headers: dict[str, str]) -> None:
    first_parent = create_category(client, auth_headers, "خشکبار")
    second_parent = create_category(client, auth_headers, "مواد غذایی")
    child = create_category(client, auth_headers, "بادام", first_parent["id"])

    response = client.patch(
        f"/api/v1/categories/{child['id']}",
        json={"name": "بادام ایرانی", "parent_id": second_parent["id"]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "بادام ایرانی"
    assert response.json()["parent_id"] == second_parent["id"]


def test_category_rejects_self_parent_and_cycle(client: TestClient, auth_headers: dict[str, str]) -> None:
    root = create_category(client, auth_headers, "ریشه")
    child = create_category(client, auth_headers, "فرزند", root["id"])
    grandchild = create_category(client, auth_headers, "نوه", child["id"])

    self_parent = client.patch(
        f"/api/v1/categories/{root['id']}",
        json={"parent_id": root["id"]},
        headers=auth_headers,
    )
    cycle = client.patch(
        f"/api/v1/categories/{root['id']}",
        json={"parent_id": grandchild["id"]},
        headers=auth_headers,
    )

    assert self_parent.status_code == 422
    assert "والد خودش" in self_parent.json()["detail"]
    assert cycle.status_code == 409
    assert "چرخه" in cycle.json()["detail"]


def test_category_rejects_duplicate_name_in_same_parent(client: TestClient, auth_headers: dict[str, str]) -> None:
    parent = create_category(client, auth_headers, "حبوبات")
    create_category(client, auth_headers, "عدس", parent["id"])

    duplicate = client.post(
        "/api/v1/categories",
        json={"name": "  عدس  ", "parent_id": parent["id"]},
        headers=auth_headers,
    )
    other_level = client.post(
        "/api/v1/categories",
        json={"name": "عدس"},
        headers=auth_headers,
    )

    assert duplicate.status_code == 409
    assert "همین سطح" in duplicate.json()["detail"]
    assert other_level.status_code == 201


def test_category_can_be_soft_deactivated(client: TestClient, auth_headers: dict[str, str], db_session: Session) -> None:
    category = create_category(client, auth_headers, "قدیمی")

    response = client.delete(f"/api/v1/categories/{category['id']}", headers=auth_headers)
    listing = client.get("/api/v1/categories", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert category["id"] not in {item["id"] for item in listing.json()}
    assert db_session.get(Category, category["id"]) is not None


def test_category_deactivation_is_blocked_by_active_child(client: TestClient, auth_headers: dict[str, str]) -> None:
    parent = create_category(client, auth_headers, "والد")
    create_category(client, auth_headers, "فرزند", parent["id"])

    response = client.delete(f"/api/v1/categories/{parent['id']}", headers=auth_headers)

    assert response.status_code == 409
    assert "فرزند فعال" in response.json()["detail"]


def test_category_deactivation_is_blocked_by_active_product(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
) -> None:
    category = create_category(client, auth_headers, "کالادار")
    db_session.add(Product(name="محصول فعال", category_id=category["id"]))
    db_session.commit()

    response = client.delete(f"/api/v1/categories/{category['id']}", headers=auth_headers)

    assert response.status_code == 409
    assert "کالای فعال" in response.json()["detail"]


def create_unit(client: TestClient, auth_headers: dict[str, str], name: str, symbol: str) -> dict:
    response = client.post("/api/v1/units", json={"name": name, "symbol": symbol}, headers=auth_headers)
    assert response.status_code == 201
    return response.json()


def create_product(
    client: TestClient,
    auth_headers: dict[str, str],
    name: str,
    category_id: int | None = None,
) -> dict:
    response = client.post(
        "/api/v1/products",
        json={"name": name, "description": "توضیح", "category_id": category_id},
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()


def test_unit_create_trims_and_update_changes_fields(client: TestClient, auth_headers: dict[str, str]) -> None:
    unit = create_unit(client, auth_headers, "  کیلوگرم  ", " kg ")

    response = client.patch(
        f"/api/v1/units/{unit['id']}",
        json={"name": "گرم", "symbol": "g"},
        headers=auth_headers,
    )

    assert unit["name"] == "کیلوگرم"
    assert unit["symbol"] == "kg"
    assert response.status_code == 200
    assert response.json()["name"] == "گرم"
    assert response.json()["symbol"] == "g"


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"name": "کیلوگرم", "symbol": "KG2"}, "نام"),
        ({"name": "واحد دیگر", "symbol": "KG"}, "نماد"),
    ],
)
def test_unit_rejects_case_insensitive_duplicates(
    client: TestClient,
    auth_headers: dict[str, str],
    payload: dict,
    expected: str,
) -> None:
    create_unit(client, auth_headers, "کیلوگرم", "kg")

    response = client.post("/api/v1/units", json=payload, headers=auth_headers)

    assert response.status_code == 409
    assert expected in response.json()["detail"]


def test_unit_soft_delete_and_missing_record_return_404(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
) -> None:
    unit = create_unit(client, auth_headers, "بسته", "pack")

    deleted = client.delete(f"/api/v1/units/{unit['id']}", headers=auth_headers)
    repeated = client.patch(f"/api/v1/units/{unit['id']}", json={"name": "کارتن"}, headers=auth_headers)

    assert deleted.status_code == 200
    assert deleted.json()["is_active"] is False
    assert repeated.status_code == 404
    assert db_session.get(Unit, unit["id"]) is not None


def test_unit_deactivation_is_blocked_by_active_variant(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    unit = create_unit(client, auth_headers, "کیلوگرم", "kg")
    product = create_product(client, auth_headers, "برنج")
    variant = client.post(
        "/api/v1/product-variants",
        json={"product_id": product["id"], "unit_id": unit["id"], "name": "برنج کیلویی", "retail_price_rial": 1},
        headers=auth_headers,
    )
    assert variant.status_code == 201

    response = client.delete(f"/api/v1/units/{unit['id']}", headers=auth_headers)

    assert response.status_code == 409
    assert "گونه کالای فعال" in response.json()["detail"]


def test_product_create_update_and_category_validation(client: TestClient, auth_headers: dict[str, str]) -> None:
    first_category = create_category(client, auth_headers, "حبوبات")
    second_category = create_category(client, auth_headers, "غلات")
    product = create_product(client, auth_headers, "  عدس  ", first_category["id"])

    updated = client.patch(
        f"/api/v1/products/{product['id']}",
        json={"name": "عدس سبز", "description": "محصول تازه", "category_id": second_category["id"]},
        headers=auth_headers,
    )
    invalid = client.post(
        "/api/v1/products",
        json={"name": "نامعتبر", "category_id": 9999},
        headers=auth_headers,
    )

    assert product["name"] == "عدس"
    assert updated.status_code == 200
    assert updated.json()["category_id"] == second_category["id"]
    assert invalid.status_code == 404


def test_product_rejects_duplicate_name_in_same_category(client: TestClient, auth_headers: dict[str, str]) -> None:
    first_category = create_category(client, auth_headers, "حبوبات")
    second_category = create_category(client, auth_headers, "غلات")
    create_product(client, auth_headers, "Rice", first_category["id"])

    duplicate = client.post(
        "/api/v1/products",
        json={"name": "  rice  ", "category_id": first_category["id"]},
        headers=auth_headers,
    )
    other_category = client.post(
        "/api/v1/products",
        json={"name": "RICE", "category_id": second_category["id"]},
        headers=auth_headers,
    )

    assert duplicate.status_code == 409
    assert "همین دسته" in duplicate.json()["detail"]
    assert other_category.status_code == 201


def test_unit_and_product_updates_reject_duplicate_values(client: TestClient, auth_headers: dict[str, str]) -> None:
    first_unit = create_unit(client, auth_headers, "کیلوگرم", "kg")
    second_unit = create_unit(client, auth_headers, "بسته", "pack")
    category = create_category(client, auth_headers, "غلات")
    first_product = create_product(client, auth_headers, "Rice", category["id"])
    second_product = create_product(client, auth_headers, "Wheat", category["id"])

    unit_response = client.patch(
        f"/api/v1/units/{second_unit['id']}",
        json={"name": first_unit["name"].upper()},
        headers=auth_headers,
    )
    product_response = client.patch(
        f"/api/v1/products/{second_product['id']}",
        json={"name": first_product["name"].lower()},
        headers=auth_headers,
    )

    assert unit_response.status_code == 409
    assert product_response.status_code == 409


def test_product_soft_delete_and_blocked_delete(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
) -> None:
    unit = create_unit(client, auth_headers, "عدد", "qty")
    blocked = create_product(client, auth_headers, "محصول دارای گونه")
    free = create_product(client, auth_headers, "محصول بدون گونه")
    db_session.add(ProductVariant(product_id=blocked["id"], unit_id=unit["id"], name="گونه فعال"))
    db_session.commit()

    blocked_response = client.delete(f"/api/v1/products/{blocked['id']}", headers=auth_headers)
    deleted = client.delete(f"/api/v1/products/{free['id']}", headers=auth_headers)

    assert blocked_response.status_code == 409
    assert "گونه فعال" in blocked_response.json()["detail"]
    assert deleted.status_code == 200
    assert deleted.json()["is_active"] is False
    assert db_session.get(Product, free["id"]) is not None


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("patch", "/api/v1/units/1", {"name": "واحد"}),
        ("delete", "/api/v1/units/1", None),
        ("patch", "/api/v1/products/1", {"name": "کالا"}),
        ("delete", "/api/v1/products/1", None),
    ],
)
def test_catalog_mutations_require_authentication(
    client: TestClient,
    method: str,
    path: str,
    payload: dict | None,
) -> None:
    response = client.request(method, path, json=payload)

    assert response.status_code == 401
