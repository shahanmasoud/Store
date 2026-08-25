from collections.abc import Generator

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.catalog import ProductVariant
from app.models.purchases import InventoryItem, PurchaseInvoice
from app.models.sales import Payment, SaleInvoice
from app.models.user import User
from app.scripts.seed_demo import DEMO_PURCHASE_NOTE, DEMO_SALE_REFERENCE, seed_demo

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as db:
        yield db

    Base.metadata.drop_all(bind=engine)


def test_seed_demo_creates_practical_local_data() -> None:
    with next(db_session()) as db:
        result = seed_demo(db)

        assert result["admin_username"] == "admin"
        assert result["demo_variants"] == 3
        assert result["created_purchase"] is True
        assert result["created_sale"] is True
        assert db.scalar(select(User).where(User.username == "admin")) is not None
        assert db.scalar(select(ProductVariant).where(ProductVariant.sku == "DEMO-BEAN-PINTO")) is not None
        assert db.scalar(select(PurchaseInvoice).where(PurchaseInvoice.note == DEMO_PURCHASE_NOTE)) is not None
        assert db.scalar(select(SaleInvoice).where(SaleInvoice.customer_name == "مشتری نمونه فروشگاه")) is not None
        assert db.scalar(select(Payment).where(Payment.reference_number == DEMO_SALE_REFERENCE)) is not None
        assert len(list(db.scalars(select(InventoryItem)))) == 3


def test_seed_demo_is_idempotent() -> None:
    with next(db_session()) as db:
        first = seed_demo(db)
        second = seed_demo(db)

        assert first["created_purchase"] is True
        assert first["created_sale"] is True
        assert second["created_purchase"] is False
        assert second["created_sale"] is False
        assert len(list(db.scalars(select(ProductVariant).where(ProductVariant.sku.like("DEMO-%"))))) == 3
        assert len(list(db.scalars(select(PurchaseInvoice).where(PurchaseInvoice.note == DEMO_PURCHASE_NOTE)))) == 1
        assert len(list(db.scalars(select(Payment).where(Payment.reference_number == DEMO_SALE_REFERENCE)))) == 1
