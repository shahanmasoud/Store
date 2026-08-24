from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import TEHRAN_TIMEZONE, utc_now
from app.db.base import Base
from app.models.catalog import TimestampMixin


class OnlineChannel(Base, TimestampMixin):
    __tablename__ = "online_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)

    price_rules: Mapped[list["OnlinePriceRule"]] = relationship(back_populates="channel")
    reservations: Mapped[list["StockReservation"]] = relationship(back_populates="channel")
    orders: Mapped[list["OnlineOrder"]] = relationship(back_populates="channel")


class OnlinePriceRule(Base, TimestampMixin):
    __tablename__ = "online_price_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("online_channels.id"), nullable=False, index=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id"), nullable=False, index=True)
    price_rial: Mapped[int] = mapped_column(Integer, nullable=False)
    min_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("1"), nullable=False)
    starts_jalali_date: Mapped[str | None] = mapped_column(String(10), index=True)
    ends_jalali_date: Mapped[str | None] = mapped_column(String(10), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    channel: Mapped[OnlineChannel] = relationship(back_populates="price_rules")


class StockReservation(Base, TimestampMixin):
    __tablename__ = "stock_reservations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("online_channels.id"), nullable=False, index=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id"), nullable=False, index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("online_orders.id"), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="reserved", nullable=False, index=True)
    expires_jalali_date: Mapped[str | None] = mapped_column(String(10), index=True)
    local_time: Mapped[str] = mapped_column(String(5), nullable=False)
    timezone: Mapped[str] = mapped_column(String(40), default=TEHRAN_TIMEZONE, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    channel: Mapped[OnlineChannel] = relationship(back_populates="reservations")
    order: Mapped["OnlineOrder | None"] = relationship(back_populates="reservations")


class OnlineOrder(Base, TimestampMixin):
    __tablename__ = "online_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("online_channels.id"), nullable=False, index=True)
    external_order_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    customer_name: Mapped[str | None] = mapped_column(String(160))
    customer_phone: Mapped[str | None] = mapped_column(String(40))
    subtotal_rial: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_amount_rial: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_rial: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    jalali_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    local_time: Mapped[str] = mapped_column(String(5), nullable=False)
    timezone: Mapped[str] = mapped_column(String(40), default=TEHRAN_TIMEZONE, nullable=False)
    occurred_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    channel: Mapped[OnlineChannel] = relationship(back_populates="orders")
    items: Mapped[list["OnlineOrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    reservations: Mapped[list[StockReservation]] = relationship(back_populates="order")


class OnlineOrderItem(Base, TimestampMixin):
    __tablename__ = "online_order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("online_orders.id"), nullable=False, index=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id"), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_price_rial: Mapped[int] = mapped_column(Integer, nullable=False)
    line_total_rial: Mapped[int] = mapped_column(Integer, nullable=False)
    product_snapshot: Mapped[str] = mapped_column(String(180), nullable=False)

    order: Mapped[OnlineOrder] = relationship(back_populates="items")
