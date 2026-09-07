from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.time import utc_now
from app.models.catalog import ProductVariant
from app.models.purchases import (
    InventoryItem,
    InventoryTransaction,
    PurchaseInvoice,
    PurchaseInvoiceItem,
    PurchaseLot,
    Supplier,
)
from app.models.user import User
from app.schemas.purchases import (
    InventoryAdjustmentCreate,
    InventoryRead,
    InventoryTransactionRead,
    InventoryUpdate,
    PurchaseInvoiceCreate,
    money_from_quantity,
)


def _round_rial(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _get_purchase_or_404(db: Session, invoice_id: int) -> PurchaseInvoice:
    invoice = db.scalar(
        select(PurchaseInvoice)
        .options(selectinload(PurchaseInvoice.items))
        .where(PurchaseInvoice.id == invoice_id)
    )
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="فاکتور خرید پیدا نشد.")
    return invoice


def _inventory_for_update(db: Session, variant_id: int) -> InventoryItem:
    inventory = db.scalar(select(InventoryItem).where(InventoryItem.variant_id == variant_id))
    if inventory:
        return inventory
    inventory = InventoryItem(variant_id=variant_id, quantity_on_hand=Decimal("0"), weighted_average_cost_rial=0)
    db.add(inventory)
    db.flush()
    return inventory


def _apply_purchase_to_inventory(db: Session, invoice: PurchaseInvoice, item: PurchaseInvoiceItem) -> None:
    inventory = _inventory_for_update(db, item.variant_id)
    old_qty = Decimal(inventory.quantity_on_hand)
    new_qty = Decimal(item.quantity)
    new_total_cost = Decimal(item.line_total_rial)
    combined_qty = old_qty + new_qty
    if combined_qty <= 0:
        inventory.weighted_average_cost_rial = 0
    else:
        old_total_cost = old_qty * Decimal(inventory.weighted_average_cost_rial)
        inventory.weighted_average_cost_rial = _round_rial((old_total_cost + new_total_cost) / combined_qty)
    inventory.quantity_on_hand = combined_qty

    db.add(
        InventoryTransaction(
            variant_id=item.variant_id,
            purchase_invoice_id=invoice.id,
            purchase_invoice_item_id=item.id,
            transaction_type="purchase_in",
            quantity_delta=item.quantity,
            unit_cost_rial=item.unit_cost_rial,
            jalali_date=invoice.jalali_date,
            local_time=invoice.local_time,
            note=f"ورود از فاکتور {invoice.invoice_number}",
        )
    )


def create_purchase(db: Session, payload: PurchaseInvoiceCreate) -> PurchaseInvoice:
    variant_ids = {item.variant_id for item in payload.items}
    variants = {
        variant.id: variant
        for variant in db.scalars(
            select(ProductVariant).where(ProductVariant.id.in_(variant_ids), ProductVariant.is_active.is_(True))
        )
    }
    missing = variant_ids - set(variants)
    if missing:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"کالای فعال پیدا نشد: {sorted(missing)}")

    supplier_name = payload.supplier_name
    if payload.supplier_id:
        supplier = db.get(Supplier, payload.supplier_id)
        if not supplier or not supplier.is_active:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="تأمین‌کننده فعال پیدا نشد.")
        supplier_name = supplier.name

    subtotal = sum(money_from_quantity(item.quantity, item.unit_cost_rial) + item.extra_cost_rial for item in payload.items)
    total = subtotal + payload.extra_cost_rial - payload.discount_amount_rial
    if total < 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="جمع فاکتور خرید نمی‌تواند منفی باشد.")

    invoice = PurchaseInvoice(
        supplier_id=payload.supplier_id,
        supplier_name=supplier_name,
        subtotal_rial=subtotal,
        discount_amount_rial=payload.discount_amount_rial,
        extra_cost_rial=payload.extra_cost_rial,
        total_rial=total,
        paid_total_rial=min(payload.paid_total_rial, total),
        due_total_rial=max(total - payload.paid_total_rial, 0),
        jalali_date=payload.jalali_date,
        local_time=payload.local_time,
        note=payload.note,
    )
    db.add(invoice)
    db.flush()
    invoice.invoice_number = f"P-{invoice.id:06d}"

    for payload_item in payload.items:
        line_total = money_from_quantity(payload_item.quantity, payload_item.unit_cost_rial) + payload_item.extra_cost_rial
        item = PurchaseInvoiceItem(
            invoice_id=invoice.id,
            variant_id=payload_item.variant_id,
            quantity=payload_item.quantity,
            unit_cost_rial=payload_item.unit_cost_rial,
            extra_cost_rial=payload_item.extra_cost_rial,
            line_total_rial=line_total,
        )
        db.add(item)
        db.flush()
        db.add(
            PurchaseLot(
                variant_id=item.variant_id,
                purchase_invoice_item_id=item.id,
                original_quantity=item.quantity,
                remaining_quantity=item.quantity,
                unit_cost_rial=item.unit_cost_rial,
                total_cost_rial=item.line_total_rial,
                jalali_date=invoice.jalali_date,
                local_time=invoice.local_time,
            )
        )
        _apply_purchase_to_inventory(db, invoice, item)

    db.commit()
    return _get_purchase_or_404(db, invoice.id)


def list_purchases(db: Session) -> list[PurchaseInvoice]:
    return list(
        db.scalars(
            select(PurchaseInvoice).options(selectinload(PurchaseInvoice.items)).order_by(PurchaseInvoice.id.desc())
        )
    )


def get_purchase(db: Session, invoice_id: int) -> PurchaseInvoice:
    return _get_purchase_or_404(db, invoice_id)


def cancel_purchase(db: Session, invoice_id: int) -> PurchaseInvoice:
    invoice = _get_purchase_or_404(db, invoice_id)
    if invoice.status == "canceled":
        return invoice

    variant_totals: dict[int, dict[str, Decimal]] = {}
    for item in invoice.items:
        totals = variant_totals.setdefault(item.variant_id, {"quantity": Decimal("0"), "cost": Decimal("0")})
        totals["quantity"] += Decimal(item.quantity)
        totals["cost"] += Decimal(item.line_total_rial)

    inventories: dict[int, InventoryItem] = {}
    for variant_id, totals in variant_totals.items():
        inventory = _inventory_for_update(db, variant_id)
        inventories[variant_id] = inventory
        if Decimal(inventory.quantity_on_hand) < totals["quantity"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="موجودی برای لغو این خرید کافی نیست.",
            )

        last_invoice_transaction_id = db.scalar(
            select(func.max(InventoryTransaction.id)).where(
                InventoryTransaction.variant_id == variant_id,
                InventoryTransaction.purchase_invoice_id == invoice.id,
                InventoryTransaction.transaction_type == "purchase_in",
            )
        )
        has_later_movement = last_invoice_transaction_id is not None and db.scalar(
            select(InventoryTransaction.id).where(
                InventoryTransaction.variant_id == variant_id,
                InventoryTransaction.id > last_invoice_transaction_id,
            ).limit(1)
        )
        if has_later_movement is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="برای این کالا پس از خرید گردش دیگری ثبت شده است؛ برای حفظ صحت بهای انبار، به‌جای لغو از اصلاح موجودی استفاده کنید.",
            )

    final_costs: dict[int, int] = {}
    running_balances: dict[int, Decimal] = {}
    cancellation_plan: dict[int, tuple[Decimal, int]] = {}
    for variant_id, totals in variant_totals.items():
        inventory = inventories[variant_id]
        old_qty = Decimal(inventory.quantity_on_hand)
        remaining_qty = old_qty - totals["quantity"]
        old_total_cost = old_qty * Decimal(inventory.weighted_average_cost_rial)
        remaining_cost = old_total_cost - totals["cost"]
        if remaining_cost < 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="لغو این خرید ارزش انبار را منفی می‌کند؛ از اصلاح موجودی استفاده کنید.",
            )
        next_cost = _round_rial(remaining_cost / remaining_qty) if remaining_qty > 0 else 0
        cancellation_plan[variant_id] = (remaining_qty, next_cost)
        final_costs[variant_id] = next_cost
        running_balances[variant_id] = old_qty

    for variant_id, (remaining_qty, next_cost) in cancellation_plan.items():
        inventories[variant_id].quantity_on_hand = remaining_qty
        inventories[variant_id].weighted_average_cost_rial = next_cost

    for item in invoice.items:
        running_balances[item.variant_id] -= Decimal(item.quantity)
        db.add(
            InventoryTransaction(
                variant_id=item.variant_id,
                purchase_invoice_id=invoice.id,
                purchase_invoice_item_id=item.id,
                transaction_type="cancel_purchase",
                quantity_delta=-Decimal(item.quantity),
                quantity_balance_after=running_balances[item.variant_id],
                unit_cost_rial=item.unit_cost_rial,
                weighted_average_cost_after_rial=final_costs[item.variant_id],
                jalali_date=invoice.jalali_date,
                local_time=invoice.local_time,
                note=f"لغو فاکتور {invoice.invoice_number}",
            )
        )
        for lot in item.lots:
            lot.status = "canceled"
            lot.is_active = False
            lot.remaining_quantity = Decimal("0")

    invoice.status = "canceled"
    invoice.is_active = False
    invoice.canceled_at_utc = utc_now()
    db.commit()
    return _get_purchase_or_404(db, invoice.id)


def list_inventory(db: Session) -> list[InventoryRead]:
    rows = db.execute(
        select(InventoryItem, ProductVariant)
        .join(ProductVariant, ProductVariant.id == InventoryItem.variant_id)
        .order_by(ProductVariant.name)
    ).all()
    return [
        InventoryRead(
            id=inventory.id,
            variant_id=inventory.variant_id,
            variant_name=variant.name,
            quantity_on_hand=inventory.quantity_on_hand,
            weighted_average_cost_rial=inventory.weighted_average_cost_rial,
            reorder_level=inventory.reorder_level,
        )
        for inventory, variant in rows
    ]


def update_inventory(db: Session, inventory_id: int, payload: InventoryUpdate) -> InventoryRead:
    row = db.execute(
        select(InventoryItem, ProductVariant)
        .join(ProductVariant, ProductVariant.id == InventoryItem.variant_id)
        .where(InventoryItem.id == inventory_id)
    ).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ردیف موجودی پیدا نشد.")

    inventory, variant = row
    inventory.reorder_level = payload.reorder_level
    db.commit()
    db.refresh(inventory)
    return InventoryRead(
        id=inventory.id,
        variant_id=inventory.variant_id,
        variant_name=variant.name,
        quantity_on_hand=inventory.quantity_on_hand,
        weighted_average_cost_rial=inventory.weighted_average_cost_rial,
        reorder_level=inventory.reorder_level,
    )


def create_inventory_adjustment(
    db: Session,
    payload: InventoryAdjustmentCreate,
    *,
    actor: User,
) -> InventoryTransactionRead:
    variant = db.scalar(
        select(ProductVariant).where(
            ProductVariant.id == payload.variant_id,
            ProductVariant.is_active.is_(True),
        )
    )
    if variant is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="کالای فعال پیدا نشد.")

    inventory = db.scalar(
        select(InventoryItem).where(InventoryItem.variant_id == payload.variant_id).with_for_update()
    )
    current_quantity = Decimal(inventory.quantity_on_hand) if inventory else Decimal("0")

    if payload.adjustment_type == "initial":
        has_history = db.scalar(
            select(InventoryTransaction.id).where(InventoryTransaction.variant_id == payload.variant_id).limit(1)
        )
        if current_quantity != 0 or has_history is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="موجودی اولیه فقط برای کالای بدون موجودی و بدون سابقه گردش قابل ثبت است.",
            )

    if payload.adjustment_type == "decrease" and payload.quantity > current_quantity:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="موجودی برای این کاهش کافی نیست.")

    if inventory is None:
        inventory = InventoryItem(
            variant_id=payload.variant_id,
            quantity_on_hand=Decimal("0"),
            weighted_average_cost_rial=0,
        )
        db.add(inventory)
        db.flush()

    old_cost = inventory.weighted_average_cost_rial
    if payload.adjustment_type in {"increase", "initial"}:
        next_quantity = current_quantity + payload.quantity
        inbound_cost = Decimal(payload.unit_cost_rial or 0)
        inventory.weighted_average_cost_rial = _round_rial(
            ((current_quantity * Decimal(old_cost)) + (payload.quantity * inbound_cost)) / next_quantity
        )
        quantity_delta = payload.quantity
    else:
        next_quantity = current_quantity - payload.quantity
        quantity_delta = -payload.quantity
        # A stock decrease removes units at the current weighted-average cost.
        # The per-unit average remains unchanged while stock exists.
        if next_quantity == 0:
            inventory.weighted_average_cost_rial = 0

    inventory.quantity_on_hand = next_quantity
    transaction = InventoryTransaction(
        variant_id=payload.variant_id,
        transaction_type=f"adjustment_{payload.adjustment_type}",
        adjustment_type=payload.adjustment_type,
        actor_user_id=actor.id,
        actor_username=actor.username,
        actor_full_name=actor.full_name,
        quantity_delta=quantity_delta,
        quantity_balance_after=next_quantity,
        unit_cost_rial=(payload.unit_cost_rial if payload.adjustment_type != "decrease" else old_cost),
        weighted_average_cost_after_rial=inventory.weighted_average_cost_rial,
        jalali_date=payload.jalali_date,
        local_time=payload.local_time,
        note=payload.reason,
        reason=payload.reason,
    )
    db.add(transaction)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(transaction)
    return InventoryTransactionRead(
        id=transaction.id,
        variant_id=transaction.variant_id,
        variant_name=variant.name,
        purchase_invoice_id=None,
        purchase_invoice_item_id=None,
        sale_invoice_id=None,
        sale_invoice_item_id=None,
        transaction_type=transaction.transaction_type,
        adjustment_type=transaction.adjustment_type,
        actor_user_id=transaction.actor_user_id,
        actor_username=transaction.actor_username,
        actor_full_name=transaction.actor_full_name,
        quantity_delta=transaction.quantity_delta,
        balance_after=next_quantity,
        quantity_balance_after=transaction.quantity_balance_after,
        unit_cost_rial=transaction.unit_cost_rial,
        weighted_average_cost_after_rial=transaction.weighted_average_cost_after_rial,
        jalali_date=transaction.jalali_date,
        local_time=transaction.local_time,
        note=transaction.note,
        reason=transaction.reason,
        occurred_at_utc=transaction.occurred_at_utc.isoformat(),
    )


def list_inventory_transactions(
    db: Session,
    *,
    variant_id: int | None = None,
    limit: int = 50,
) -> list[InventoryTransactionRead]:
    rows = db.execute(
        select(InventoryTransaction, ProductVariant)
        .join(ProductVariant, ProductVariant.id == InventoryTransaction.variant_id)
        .order_by(InventoryTransaction.id)
    ).all()

    balances: dict[int, Decimal] = {}
    result: list[InventoryTransactionRead] = []
    for transaction, variant in rows:
        balance = balances.get(transaction.variant_id, Decimal("0")) + Decimal(transaction.quantity_delta)
        balances[transaction.variant_id] = balance
        displayed_balance = (
            Decimal(transaction.quantity_balance_after)
            if transaction.quantity_balance_after is not None
            else balance
        )
        if variant_id is not None and transaction.variant_id != variant_id:
            continue
        result.append(
            InventoryTransactionRead(
                id=transaction.id,
                variant_id=transaction.variant_id,
                variant_name=variant.name,
                purchase_invoice_id=transaction.purchase_invoice_id,
                purchase_invoice_item_id=transaction.purchase_invoice_item_id,
                sale_invoice_id=transaction.sale_invoice_id,
                sale_invoice_item_id=transaction.sale_invoice_item_id,
                transaction_type=transaction.transaction_type,
                adjustment_type=transaction.adjustment_type,
                actor_user_id=transaction.actor_user_id,
                actor_username=transaction.actor_username,
                actor_full_name=transaction.actor_full_name,
                quantity_delta=transaction.quantity_delta,
                balance_after=displayed_balance,
                quantity_balance_after=transaction.quantity_balance_after,
                unit_cost_rial=transaction.unit_cost_rial,
                weighted_average_cost_after_rial=transaction.weighted_average_cost_after_rial,
                jalali_date=transaction.jalali_date,
                local_time=transaction.local_time,
                note=transaction.note,
                reason=transaction.reason,
                occurred_at_utc=transaction.occurred_at_utc.isoformat(),
            )
        )
    return list(reversed(result[-limit:]))
