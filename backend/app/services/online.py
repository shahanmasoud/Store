from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.catalog import ProductVariant
from app.models.online import OnlineChannel, OnlineOrder, OnlineOrderItem, OnlinePriceRule, StockReservation
from app.core.time import current_jalali_date
from app.models.purchases import InventoryItem
from app.schemas.online import (
    OnlineCatalogItemRead,
    OnlineChannelCreate,
    OnlineOrderCreate,
    OnlinePriceRuleCreate,
    StockReservationRead,
    StockReservationCreate,
)


def _token_hash(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def _money(quantity: Decimal, price_rial: int) -> int:
    return int((quantity * price_rial).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _channel_or_404(db: Session, channel_id: int) -> OnlineChannel:
    channel = db.scalar(
        select(OnlineChannel).where(
            OnlineChannel.id == channel_id,
            OnlineChannel.is_active.is_(True),
        )
    )
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="کانال آنلاین پیدا نشد.")
    return channel


def channel_from_token(db: Session, token: str) -> OnlineChannel:
    channel = db.scalar(
        select(OnlineChannel).where(
            OnlineChannel.token_hash == _token_hash(token),
            OnlineChannel.is_active.is_(True),
        )
    )
    if not channel:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="توکن کانال آنلاین معتبر نیست.")
    return channel


def _variant_or_422(db: Session, variant_id: int) -> ProductVariant:
    variant = db.scalar(
        select(ProductVariant).where(
            ProductVariant.id == variant_id,
            ProductVariant.is_active.is_(True),
        )
    )
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="کالای آنلاین پیدا نشد یا غیرفعال است.",
        )
    return variant


def _available_quantity(db: Session, variant_id: int, effective_jalali_date: str) -> Decimal:
    inventory = db.scalar(select(InventoryItem).where(InventoryItem.variant_id == variant_id))
    on_hand = inventory.quantity_on_hand if inventory else Decimal("0")
    reserved = db.scalar(
        select(func.coalesce(func.sum(StockReservation.quantity), 0)).where(
            StockReservation.variant_id == variant_id,
            StockReservation.status == "reserved",
            StockReservation.is_active.is_(True),
            (StockReservation.expires_jalali_date.is_(None))
            | (StockReservation.expires_jalali_date >= effective_jalali_date),
        )
    )
    return on_hand - Decimal(reserved or 0)


def _online_price(
    db: Session,
    channel_id: int,
    variant: ProductVariant,
    quantity: Decimal,
    jalali_date: str | None = None,
) -> int:
    filters = [
        OnlinePriceRule.channel_id == channel_id,
        OnlinePriceRule.variant_id == variant.id,
        OnlinePriceRule.min_quantity <= quantity,
        OnlinePriceRule.is_active.is_(True),
    ]
    if jalali_date is not None:
        filters.extend(
            [
                (OnlinePriceRule.starts_jalali_date.is_(None)) | (OnlinePriceRule.starts_jalali_date <= jalali_date),
                (OnlinePriceRule.ends_jalali_date.is_(None)) | (OnlinePriceRule.ends_jalali_date >= jalali_date),
            ]
        )
    rule = db.scalar(
        select(OnlinePriceRule)
        .where(*filters)
        .order_by(OnlinePriceRule.min_quantity.desc(), OnlinePriceRule.id.desc())
    )
    return rule.price_rial if rule else variant.retail_price_rial


def create_channel(db: Session, payload: OnlineChannelCreate) -> OnlineChannel:
    token_hash = _token_hash(payload.token)
    exists = db.scalar(select(OnlineChannel).where(OnlineChannel.token_hash == token_hash))
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="توکن کانال آنلاین تکراری است.")
    channel = OnlineChannel(**payload.model_dump(exclude={"token"}), token_hash=token_hash)
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return channel


def list_channels(db: Session) -> list[OnlineChannel]:
    return list(db.scalars(select(OnlineChannel).where(OnlineChannel.is_active.is_(True)).order_by(OnlineChannel.name)))


def create_price_rule(db: Session, payload: OnlinePriceRuleCreate) -> OnlinePriceRule:
    _channel_or_404(db, payload.channel_id)
    _variant_or_422(db, payload.variant_id)
    if payload.starts_jalali_date and payload.ends_jalali_date and payload.starts_jalali_date > payload.ends_jalali_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="بازه تاریخ قانون قیمت معتبر نیست.")
    rule = OnlinePriceRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def list_price_rules(
    db: Session,
    channel_id: int | None = None,
    variant_id: int | None = None,
) -> list[OnlinePriceRule]:
    query = select(OnlinePriceRule).where(OnlinePriceRule.is_active.is_(True))
    if channel_id is not None:
        query = query.where(OnlinePriceRule.channel_id == channel_id)
    if variant_id is not None:
        query = query.where(OnlinePriceRule.variant_id == variant_id)
    return list(db.scalars(query.order_by(OnlinePriceRule.id.desc())))


def list_catalog(db: Session, channel: OnlineChannel) -> list[OnlineCatalogItemRead]:
    effective_date = current_jalali_date()
    variants = list(db.scalars(select(ProductVariant).where(ProductVariant.is_active.is_(True)).order_by(ProductVariant.name)))
    return [
        OnlineCatalogItemRead(
            variant_id=variant.id,
            name=variant.name,
            sku=variant.sku,
            retail_price_rial=variant.retail_price_rial,
            online_price_rial=_online_price(db, channel.id, variant, Decimal("1"), effective_date),
            available_quantity=_available_quantity(db, variant.id, effective_date),
        )
        for variant in variants
    ]


def create_reservation(db: Session, payload: StockReservationCreate) -> StockReservation:
    effective_date = current_jalali_date()
    _channel_or_404(db, payload.channel_id)
    _variant_or_422(db, payload.variant_id)
    if payload.expires_jalali_date and payload.expires_jalali_date < effective_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="تاریخ انقضای رزرو نمی‌تواند پیش از تاریخ موثر باشد.",
        )
    if _available_quantity(db, payload.variant_id, effective_date) < payload.quantity:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="موجودی قابل رزرو کافی نیست.")
    reservation = StockReservation(**payload.model_dump())
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return reservation


def list_reservations(
    db: Session,
    channel_id: int | None = None,
    variant_id: int | None = None,
    reservation_status: str | None = None,
    effective_jalali_date: str | None = None,
) -> list[StockReservationRead]:
    effective_date = effective_jalali_date or current_jalali_date()
    query = select(StockReservation).where(StockReservation.is_active.is_(True))
    if channel_id is not None:
        query = query.where(StockReservation.channel_id == channel_id)
    if variant_id is not None:
        query = query.where(StockReservation.variant_id == variant_id)
    if reservation_status is not None:
        query = query.where(StockReservation.status == reservation_status)
    reservations = list(db.scalars(query.order_by(StockReservation.id.desc())))
    return [
        StockReservationRead.model_validate(
            {
                **{
                    column.name: getattr(reservation, column.name)
                    for column in StockReservation.__table__.columns
                },
                "is_expired": bool(
                    reservation.status == "reserved"
                    and reservation.expires_jalali_date
                    and reservation.expires_jalali_date < effective_date
                ),
            }
        )
        for reservation in reservations
    ]


def create_order(db: Session, channel: OnlineChannel, payload: OnlineOrderCreate) -> OnlineOrder:
    existing = db.scalar(
        select(OnlineOrder).where(
            OnlineOrder.channel_id == channel.id,
            OnlineOrder.external_order_id == payload.external_order_id,
            OnlineOrder.is_active.is_(True),
        )
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="شناسه سفارش آنلاین تکراری است.")

    effective_date = current_jalali_date()
    variants = {_item.variant_id: _variant_or_422(db, _item.variant_id) for _item in payload.items}
    requested_by_variant: dict[int, Decimal] = {}
    for item in payload.items:
        requested_by_variant[item.variant_id] = requested_by_variant.get(item.variant_id, Decimal("0")) + item.quantity
    for variant_id, requested_quantity in requested_by_variant.items():
        if _available_quantity(db, variant_id, effective_date) < requested_quantity:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="موجودی قابل فروش آنلاین کافی نیست.")

    subtotal = 0
    lines: list[tuple[int, Decimal, int, int, str]] = []
    for item in payload.items:
        variant = variants[item.variant_id]
        price = _online_price(db, channel.id, variant, item.quantity, payload.jalali_date)
        line_total = _money(item.quantity, price)
        subtotal += line_total
        lines.append((item.variant_id, item.quantity, price, line_total, variant.name))

    total = subtotal - payload.discount_amount_rial
    if total < 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="مبلغ سفارش آنلاین منفی شده است.")

    order = OnlineOrder(
        channel_id=channel.id,
        external_order_id=payload.external_order_id,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        subtotal_rial=subtotal,
        discount_amount_rial=payload.discount_amount_rial,
        total_rial=total,
        jalali_date=payload.jalali_date,
        local_time=payload.local_time,
        note=payload.note,
    )
    db.add(order)
    db.flush()

    for variant_id, quantity, price, line_total, snapshot in lines:
        db.add(
            OnlineOrderItem(
                order_id=order.id,
                variant_id=variant_id,
                quantity=quantity,
                unit_price_rial=price,
                line_total_rial=line_total,
                product_snapshot=snapshot,
            )
        )
        db.add(
            StockReservation(
                channel_id=channel.id,
                variant_id=variant_id,
                order_id=order.id,
                quantity=quantity,
                status="reserved",
                local_time=payload.local_time,
                note=f"رزرو سفارش آنلاین {payload.external_order_id}",
            )
        )

    db.commit()
    return db.scalar(
        select(OnlineOrder)
        .options(selectinload(OnlineOrder.items))
        .where(OnlineOrder.id == order.id)
    )


def list_orders(db: Session, channel_id: int | None = None) -> list[OnlineOrder]:
    query = select(OnlineOrder).options(selectinload(OnlineOrder.items)).where(OnlineOrder.is_active.is_(True))
    if channel_id is not None:
        query = query.where(OnlineOrder.channel_id == channel_id)
    return list(db.scalars(query.order_by(OnlineOrder.id.desc())))
