from collections.abc import Generator
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1 import catalog as catalog_api
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.catalog import Category, Product, ProductVariant, Unit
from app.models.purchases import InventoryItem
from app.models.online import OnlineChannel, StockReservation
from app.models.user import User
from app.services import product_media


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
        db.add_all(
            [
                User(
                    username="admin",
                    full_name="مدیر اصلی",
                    hashed_password=get_password_hash("admin123"),
                    is_active=True,
                    is_superuser=True,
                ),
                User(
                    username="staff",
                    full_name="کاربر فروشگاه",
                    hashed_password=get_password_hash("staff1234"),
                    is_active=True,
                    is_superuser=False,
                ),
            ]
        )
        db.commit()
        yield db
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session: Session, tmp_path, monkeypatch) -> Generator[TestClient, None, None]:
    settings = SimpleNamespace(media_root=tmp_path, media_url_prefix="/media", product_image_max_bytes=5 * 1024 * 1024)
    monkeypatch.setattr(product_media, "get_settings", lambda: settings)
    monkeypatch.setattr(catalog_api, "get_settings", lambda: settings)

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _login(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _catalog_records(db: Session) -> tuple[Product, ProductVariant]:
    category = Category(name="حبوبات")
    unit = Unit(name="کیلوگرم", symbol="kg")
    db.add_all([category, unit])
    db.flush()
    product = Product(name="عدس", description="عدس تازه", category_id=category.id)
    db.add(product)
    db.flush()
    variant = ProductVariant(
        product_id=product.id,
        unit_id=unit.id,
        name="عدس کیلویی",
        sku="LENTIL-1",
        retail_price_rial=1_250_000,
    )
    db.add(variant)
    db.flush()
    db.add(InventoryItem(variant_id=variant.id, quantity_on_hand=Decimal("12.500")))
    db.commit()
    return product, variant


def _image_bytes(format_name: str = "PNG") -> bytes:
    output = BytesIO()
    Image.new("RGB", (32, 24), color=(120, 80, 40)).save(output, format=format_name)
    return output.getvalue()


def test_public_catalog_uses_database_without_auth(client: TestClient, db_session: Session) -> None:
    product, variant = _catalog_records(db_session)

    response = client.get("/api/v1/storefront/catalog")

    assert response.status_code == 200
    assert response.json() == [
        {
            "variant_id": variant.id,
            "variant_name": "عدس کیلویی",
            "sku": "LENTIL-1",
            "product_id": product.id,
            "product_name": "عدس",
            "description": "عدس تازه",
            "category_id": product.category_id,
            "category_name": "حبوبات",
            "unit_id": variant.unit_id,
            "unit_name": "کیلوگرم",
            "unit_symbol": "kg",
            "retail_price_rial": 1_250_000,
            "available_quantity": "12.500",
            "image_url": None,
        }
    ]


def test_public_catalog_filters_inactive_relations_and_clamps_negative_stock(
    client: TestClient,
    db_session: Session,
) -> None:
    product, variant = _catalog_records(db_session)
    inventory = db_session.query(InventoryItem).filter_by(variant_id=variant.id).one()
    inventory.quantity_on_hand = Decimal("-2")
    db_session.commit()

    assert client.get("/api/v1/storefront/catalog").json()[0]["available_quantity"] == "0"

    product.category.is_active = False
    db_session.commit()
    legacy_category = client.get("/api/v1/storefront/catalog").json()
    assert len(legacy_category) == 1
    assert legacy_category[0]["category_id"] is None
    assert legacy_category[0]["category_name"] is None

    product.category_id = None
    db_session.commit()
    assert len(client.get("/api/v1/storefront/catalog").json()) == 1

    variant.unit.is_active = False
    db_session.commit()
    assert client.get("/api/v1/storefront/catalog").json() == []


def test_public_catalog_subtracts_only_active_nonexpired_reservations(
    client: TestClient,
    db_session: Session,
) -> None:
    _, variant = _catalog_records(db_session)
    channel = OnlineChannel(name="فروشگاه", token_hash="a" * 64, is_active=True)
    db_session.add(channel)
    db_session.flush()
    db_session.add_all(
        [
            StockReservation(
                channel_id=channel.id,
                variant_id=variant.id,
                quantity=Decimal("2.250"),
                status="reserved",
                expires_jalali_date=None,
                local_time="10:00",
                is_active=True,
            ),
            StockReservation(
                channel_id=channel.id,
                variant_id=variant.id,
                quantity=Decimal("3"),
                status="reserved",
                expires_jalali_date="1300/01/01",
                local_time="10:00",
                is_active=True,
            ),
            StockReservation(
                channel_id=channel.id,
                variant_id=variant.id,
                quantity=Decimal("4"),
                status="released",
                expires_jalali_date=None,
                local_time="10:00",
                is_active=True,
            ),
            StockReservation(
                channel_id=channel.id,
                variant_id=variant.id,
                quantity=Decimal("5"),
                status="reserved",
                expires_jalali_date=None,
                local_time="10:00",
                is_active=False,
            ),
        ]
    )
    db_session.commit()

    item = client.get("/api/v1/storefront/catalog").json()[0]

    assert item["available_quantity"] == "10.250"


def test_superuser_can_upload_replace_and_remove_sanitized_image(
    client: TestClient,
    db_session: Session,
    tmp_path,
) -> None:
    product, _ = _catalog_records(db_session)
    headers = _login(client, "admin", "admin123")

    first = client.put(
        f"/api/v1/products/{product.id}/image",
        files={"image": ("../unsafe.png", _image_bytes("PNG"), "image/png")},
        headers=headers,
    )
    assert first.status_code == 200
    first_url = first.json()["image_url"]
    first_name = first_url.rsplit("/", 1)[-1]
    first_path = tmp_path / "products" / first_name
    assert first_url.startswith("/media/products/")
    assert first_name.endswith(".png") and "unsafe" not in first_name
    assert first_path.is_file()
    with Image.open(first_path) as saved:
        assert saved.format == "PNG"

    second = client.put(
        f"/api/v1/products/{product.id}/image",
        files={"image": ("photo.jpg", _image_bytes("JPEG"), "image/jpeg")},
        headers=headers,
    )
    assert second.status_code == 200
    second_name = second.json()["image_url"].rsplit("/", 1)[-1]
    assert second_name.endswith(".jpg") and second_name != first_name
    assert not first_path.exists()
    assert (tmp_path / "products" / second_name).is_file()

    listing = client.get("/api/v1/storefront/catalog").json()
    assert listing[0]["image_url"] == second.json()["image_url"]
    removed = client.delete(f"/api/v1/products/{product.id}/image", headers=headers)
    assert removed.status_code == 200
    assert removed.json() == {"product_id": product.id, "image_url": None}
    assert not (tmp_path / "products" / second_name).exists()


def test_image_mutations_require_superuser(client: TestClient, db_session: Session) -> None:
    product, _ = _catalog_records(db_session)
    image = {"image": ("image.png", _image_bytes(), "image/png")}

    assert client.put(f"/api/v1/products/{product.id}/image", files=image).status_code == 401
    staff_headers = _login(client, "staff", "staff1234")
    assert client.put(f"/api/v1/products/{product.id}/image", files=image, headers=staff_headers).status_code == 403
    assert client.delete(f"/api/v1/products/{product.id}/image", headers=staff_headers).status_code == 403


@pytest.mark.parametrize(
    "filename,content,content_type",
    [
        ("fake.jpg", b"this is not an image", "image/jpeg"),
        ("mismatch.jpg", None, "image/jpeg"),
        ("gif.gif", b"GIF89a", "image/gif"),
    ],
)
def test_upload_rejects_invalid_or_mismatched_content(
    client: TestClient,
    db_session: Session,
    filename: str,
    content: bytes | None,
    content_type: str,
) -> None:
    product, _ = _catalog_records(db_session)
    headers = _login(client, "admin", "admin123")
    content = _image_bytes("PNG") if content is None else content

    response = client.put(
        f"/api/v1/products/{product.id}/image",
        files={"image": (filename, content, content_type)},
        headers=headers,
    )

    assert response.status_code == 415
    assert list(product_media._product_directory().iterdir()) == []


def test_upload_rejects_oversized_file_before_decoding(client: TestClient, db_session: Session, monkeypatch, tmp_path) -> None:
    product, _ = _catalog_records(db_session)
    settings = SimpleNamespace(media_root=tmp_path, media_url_prefix="/media", product_image_max_bytes=1024)
    monkeypatch.setattr(product_media, "get_settings", lambda: settings)
    monkeypatch.setattr(catalog_api, "get_settings", lambda: settings)
    headers = _login(client, "admin", "admin123")

    response = client.put(
        f"/api/v1/products/{product.id}/image",
        files={"image": ("large.png", b"x" * 1025, "image/png")},
        headers=headers,
    )

    assert response.status_code == 413


def test_image_endpoint_rejects_inactive_or_missing_product(client: TestClient, db_session: Session) -> None:
    product, variant = _catalog_records(db_session)
    headers = _login(client, "admin", "admin123")
    variant.is_active = False
    product.is_active = False
    db_session.commit()

    inactive = client.put(
        f"/api/v1/products/{product.id}/image",
        files={"image": ("image.webp", _image_bytes("WEBP"), "image/webp")},
        headers=headers,
    )
    missing = client.delete("/api/v1/products/99999/image", headers=headers)

    assert inactive.status_code == 404
    assert missing.status_code == 404
