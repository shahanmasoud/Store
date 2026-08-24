from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import TEHRAN_TIMEZONE, utc_now
from app.db.base import Base
from app.models.catalog import TimestampMixin


class Supplier(Base, TimestampMixin):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(40))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class PurchaseInvoice(Base, TimestampMixin):
    __tablename__ = "purchase_invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    invoice_number: Mapped[str | None] = mapped_column(String(40), unique=True)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"))
    supplier_name: Mapped[str | None] = mapped_column(String(160))
    subtotal_rial: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_amount_rial: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    extra_cost_rial: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_rial: Mapped[int] = mapped_column(Integer, nullable=False)
    paid_total_rial: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    due_total_rial: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    jalali_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    local_time: Mapped[str] = mapped_column(String(5), nullable=False)
    timezone: Mapped[str] = mapped_column(String(40), default=TEHRAN_TIMEZONE, nullable=False)
    occurred_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    canceled_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(Text)

    supplier: Mapped[Supplier | None] = relationship()
    items: Mapped[list["PurchaseInvoiceItem"]] = relationship(back_populates="invoice", cascade="all, delete-orphan")


class PurchaseInvoiceItem(Base, TimestampMixin):
    __tablename__ = "purchase_invoice_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("purchase_invoices.id"), nullable=False, index=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id"), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_cost_rial: Mapped[int] = mapped_column(Integer, nullable=False)
    extra_cost_rial: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    line_total_rial: Mapped[int] = mapped_column(Integer, nullable=False)

    invoice: Mapped[PurchaseInvoice] = relationship(back_populates="items")
    lots: Mapped[list["PurchaseLot"]] = relationship(back_populates="purchase_item")


class PurchaseLot(Base, TimestampMixin):
    __tablename__ = "purchase_lots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id"), nullable=False, index=True)
    purchase_invoice_item_id: Mapped[int] = mapped_column(ForeignKey("purchase_invoice_items.id"), nullable=False)
    original_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    remaining_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_cost_rial: Mapped[int] = mapped_column(Integer, nullable=False)
    total_cost_rial: Mapped[int] = mapped_column(Integer, nullable=False)
    jalali_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    local_time: Mapped[str] = mapped_column(String(5), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    purchase_item: Mapped[PurchaseInvoiceItem] = relationship(back_populates="lots")


class InventoryItem(Base, TimestampMixin):
    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id"), unique=True, nullable=False, index=True)
    quantity_on_hand: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"), nullable=False)
    weighted_average_cost_rial: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reorder_level: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))


class InventoryTransaction(Base, TimestampMixin):
    __tablename__ = "inventory_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id"), nullable=False, index=True)
    purchase_invoice_id: Mapped[int | None] = mapped_column(ForeignKey("purchase_invoices.id"))
    purchase_invoice_item_id: Mapped[int | None] = mapped_column(ForeignKey("purchase_invoice_items.id"))
    transaction_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    quantity_delta: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_cost_rial: Mapped[int | None] = mapped_column(Integer)
    jalali_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    local_time: Mapped[str] = mapped_column(String(5), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
