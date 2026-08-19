from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import TEHRAN_TIMEZONE, utc_now
from app.db.base import Base


class TimestampMixin:
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=utc_now)


class SoftDeleteMixin:
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Unit(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)

    variants: Mapped[list["ProductVariant"]] = relationship(back_populates="unit")


class Category(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))

    parent: Mapped["Category | None"] = relationship(remote_side="Category.id", back_populates="children")
    children: Mapped[list["Category"]] = relationship(back_populates="parent")
    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))

    category: Mapped[Category | None] = relationship(back_populates="products")
    variants: Mapped[list["ProductVariant"]] = relationship(back_populates="product")


class ProductVariant(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "product_variants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    sku: Mapped[str | None] = mapped_column(String(80), unique=True)
    retail_price_rial: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wholesale_price_rial: Mapped[int | None] = mapped_column(Integer)
    min_wholesale_quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))

    product: Mapped[Product] = relationship(back_populates="variants")
    unit: Mapped[Unit] = relationship(back_populates="variants")
    prices: Mapped[list["PriceList"]] = relationship(back_populates="variant")
    price_rules: Mapped[list["PriceRule"]] = relationship(back_populates="variant")


class PriceList(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "price_lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id"), nullable=False)
    price_type: Mapped[str] = mapped_column(String(30), nullable=False)
    amount_rial: Mapped[int] = mapped_column(Integer, nullable=False)
    jalali_date: Mapped[str] = mapped_column(String(10), nullable=False)
    local_time: Mapped[str] = mapped_column(String(5), nullable=False)
    timezone: Mapped[str] = mapped_column(String(40), default=TEHRAN_TIMEZONE, nullable=False)
    occurred_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    variant: Mapped[ProductVariant] = relationship(back_populates="prices")


class PriceRule(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "price_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id"), nullable=False)
    min_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    discount_amount_rial: Mapped[int | None] = mapped_column(Integer)
    discount_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    starts_jalali_date: Mapped[str | None] = mapped_column(String(10))

    variant: Mapped[ProductVariant] = relationship(back_populates="price_rules")
