from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import select
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
from app.schemas.purchases import (
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

    for item in invoice.items:
        inventory = _inventory_for_update(db, item.variant_id)
        if Decimal(inventory.quantity_on_hand) < Decimal(item.quantity):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="موجودی برای لغو این خرید کافی نیست.",
            )

    for item in invoice.items:
        inventory = _inventory_for_update(db, item.variant_id)
        old_qty = Decimal(inventory.quantity_on_hand)
        remaining_qty = old_qty - Decimal(item.quantity)
        old_total_cost = old_qty * Decimal(inventory.weighted_average_cost_rial)
        removed_cost = Decimal(item.line_total_rial)
        inventory.quantity_on_hand = remaining_qty
        inventory.weighted_average_cost_rial = _round_rial((old_total_cost - removed_cost) / remaining_qty) if remaining_qty > 0 else 0
        db.add(
            InventoryTransaction(
                variant_id=item.variant_id,
                purchase_invoice_id=invoice.id,
                purchase_invoice_item_id=item.id,
                transaction_type="cancel_purchase",
                quantity_delta=-Decimal(item.quantity),
                unit_cost_rial=item.unit_cost_rial,
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
        if variant_id is not None and transaction.variant_id != variant_id:
            continue
        result.append(
            InventoryTransactionRead(
                id=transaction.id,
                variant_id=transaction.variant_id,
                variant_name=variant.name,
                purchase_invoice_id=transaction.purchase_invoice_id,
                purchase_invoice_item_id=transaction.purchase_invoice_item_id,
                transaction_type=transaction.transaction_type,
                quantity_delta=transaction.quantity_delta,
                balance_after=balance,
                unit_cost_rial=transaction.unit_cost_rial,
                jalali_date=transaction.jalali_date,
                local_time=transaction.local_time,
                note=transaction.note,
            )
        )
    return list(reversed(result[-limit:]))
