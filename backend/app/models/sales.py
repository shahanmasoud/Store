from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import TEHRAN_TIMEZONE, utc_now
from app.db.base import Base
from app.models.catalog import TimestampMixin


class SaleInvoice(Base, TimestampMixin):
    __tablename__ = "sale_invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    invoice_number: Mapped[str | None] = mapped_column(String(40), unique=True)
    customer_name: Mapped[str | None] = mapped_column(String(160))
    subtotal_rial: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_amount_rial: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
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

    items: Mapped[list["SaleInvoiceItem"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
    )


class SaleInvoiceItem(Base, TimestampMixin):
    __tablename__ = "sale_invoice_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("sale_invoices.id"), nullable=False, index=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id"), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_price_rial: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_amount_rial: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    line_total_rial: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_cost_rial: Mapped[int | None] = mapped_column(Integer)
    estimated_profit_rial: Mapped[int | None] = mapped_column(Integer)
    product_snapshot: Mapped[str] = mapped_column(String(180), nullable=False)

    invoice: Mapped[SaleInvoice] = relationship(back_populates="items")


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("sale_invoices.id"), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    amount_rial: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    reference_number: Mapped[str | None] = mapped_column(String(120))
    jalali_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    local_time: Mapped[str] = mapped_column(String(5), nullable=False)
    timezone: Mapped[str] = mapped_column(String(40), default=TEHRAN_TIMEZONE, nullable=False)
    occurred_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    due_jalali_date: Mapped[str | None] = mapped_column(String(10), index=True)
    note: Mapped[str | None] = mapped_column(Text)

    invoice: Mapped[SaleInvoice] = relationship(back_populates="payments")
