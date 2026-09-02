from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.time import utc_now
from app.models.catalog import ProductVariant
from app.models.purchases import InventoryItem, InventoryTransaction
from app.models.sales import Payment, SaleInvoice, SaleInvoiceItem
from app.schemas.sales import DailyJournalPaymentBreakdown, DailyJournalRead, PaymentCreate, SaleInvoiceCreate

RECEIVED_BY_DEFAULT = {"cash", "card", "transfer"}


def _gross_line_total(quantity: Decimal, unit_price_rial: int) -> int:
    return int((quantity * unit_price_rial).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _line_total(quantity: Decimal, unit_price_rial: int, discount_amount_rial: int) -> int:
    return _gross_line_total(quantity, unit_price_rial) - discount_amount_rial


def _default_payment_status(payload: PaymentCreate) -> str:
    if payload.status:
        return payload.status
    if payload.method in RECEIVED_BY_DEFAULT:
        return "received"
    return "pending"


def _get_invoice_or_404(db: Session, invoice_id: int) -> SaleInvoice:
    invoice = db.scalar(
        select(SaleInvoice)
        .options(selectinload(SaleInvoice.items), selectinload(SaleInvoice.payments))
        .where(SaleInvoice.id == invoice_id)
    )
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sale invoice not found.")
    return invoice


def create_sale(db: Session, payload: SaleInvoiceCreate) -> SaleInvoice:
    variant_ids = {item.variant_id for item in payload.items}
    variants = {
        variant.id: variant
        for variant in db.scalars(
            select(ProductVariant).where(
                ProductVariant.id.in_(variant_ids),
                ProductVariant.is_active.is_(True),
            )
        )
    }
    missing_ids = variant_ids - set(variants)
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"کالای فعال پیدا نشد: {sorted(missing_ids)}",
        )

    requested_quantities: dict[int, Decimal] = defaultdict(Decimal)
    for item in payload.items:
        requested_quantities[item.variant_id] += item.quantity
    inventories = {
        inventory.variant_id: inventory
        for inventory in db.scalars(
            select(InventoryItem).where(InventoryItem.variant_id.in_(variant_ids))
        )
    }
    insufficient = [
        variants[variant_id].name
        for variant_id, requested in requested_quantities.items()
        if variant_id not in inventories or Decimal(inventories[variant_id].quantity_on_hand) < requested
    ]
    if insufficient:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"موجودی کافی نیست: {', '.join(insufficient)}",
        )

    line_totals = [_line_total(item.quantity, item.unit_price_rial, item.discount_amount_rial) for item in payload.items]
    if any(line_total < 0 for line_total in line_totals):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Sale item total cannot be negative.",
        )

    subtotal = sum(line_totals)
    total = subtotal - payload.discount_amount_rial
    if total < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="تخفیف فاکتور نمی‌تواند از جمع ردیف‌ها بیشتر باشد.",
        )

    assigned_total = sum(payment.amount_rial for payment in payload.payments)
    if assigned_total > total:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="جمع پرداخت‌ها نمی‌تواند از مبلغ فاکتور بیشتر باشد.",
        )

    paid_total = sum(
        payment.amount_rial for payment in payload.payments if _default_payment_status(payment) == "received"
    )
    due_total = max(total - paid_total, 0)

    invoice = SaleInvoice(
        customer_name=payload.customer_name,
        subtotal_rial=subtotal,
        discount_amount_rial=payload.discount_amount_rial,
        total_rial=total,
        paid_total_rial=paid_total,
        due_total_rial=due_total,
        jalali_date=payload.jalali_date,
        local_time=payload.local_time,
        note=payload.note,
    )
    db.add(invoice)
    db.flush()
    invoice.invoice_number = f"S-{invoice.id:06d}"

    for item in payload.items:
        variant = variants[item.variant_id]
        inventory = inventories[item.variant_id]
        estimated_cost = _gross_line_total(item.quantity, inventory.weighted_average_cost_rial)
        invoice_item = SaleInvoiceItem(
            invoice_id=invoice.id,
            variant_id=item.variant_id,
            quantity=item.quantity,
            unit_price_rial=item.unit_price_rial,
            discount_amount_rial=item.discount_amount_rial,
            line_total_rial=_line_total(item.quantity, item.unit_price_rial, item.discount_amount_rial),
            estimated_cost_rial=estimated_cost,
            estimated_profit_rial=_line_total(item.quantity, item.unit_price_rial, item.discount_amount_rial)
            - estimated_cost,
            product_snapshot=variant.name,
        )
        db.add(invoice_item)
        db.flush()
        inventory.quantity_on_hand = Decimal(inventory.quantity_on_hand) - item.quantity
        db.add(
            InventoryTransaction(
                variant_id=item.variant_id,
                sale_invoice_id=invoice.id,
                sale_invoice_item_id=invoice_item.id,
                transaction_type="sale_out",
                quantity_delta=-item.quantity,
                unit_cost_rial=inventory.weighted_average_cost_rial,
                jalali_date=invoice.jalali_date,
                local_time=invoice.local_time,
                note=f"خروج بابت فاکتور {invoice.invoice_number}",
            )
        )

    for payment_payload in payload.payments:
        db.add(
            Payment(
                invoice_id=invoice.id,
                method=payment_payload.method,
                amount_rial=payment_payload.amount_rial,
                status=_default_payment_status(payment_payload),
                reference_number=payment_payload.reference_number,
                jalali_date=payment_payload.jalali_date or payload.jalali_date,
                local_time=payment_payload.local_time or payload.local_time,
                due_jalali_date=payment_payload.due_jalali_date,
                note=payment_payload.note,
            )
        )

    db.commit()
    return _get_invoice_or_404(db, invoice.id)


def list_sales(db: Session) -> list[SaleInvoice]:
    return list(
        db.scalars(
            select(SaleInvoice)
            .options(selectinload(SaleInvoice.items), selectinload(SaleInvoice.payments))
            .order_by(SaleInvoice.id.desc())
        )
    )


def get_sale(db: Session, invoice_id: int) -> SaleInvoice:
    return _get_invoice_or_404(db, invoice_id)


def cancel_sale(db: Session, invoice_id: int) -> SaleInvoice:
    invoice = _get_invoice_or_404(db, invoice_id)
    if invoice.status != "canceled":
        for item in invoice.items:
            sale_out = db.scalar(
                select(InventoryTransaction).where(
                    InventoryTransaction.sale_invoice_item_id == item.id,
                    InventoryTransaction.transaction_type == "sale_out",
                )
            )
            if sale_out is None:
                continue
            inventory = db.scalar(select(InventoryItem).where(InventoryItem.variant_id == item.variant_id))
            if inventory is None:
                inventory = InventoryItem(
                    variant_id=item.variant_id,
                    quantity_on_hand=Decimal("0"),
                    weighted_average_cost_rial=0,
                )
                db.add(inventory)
                db.flush()
            old_quantity = Decimal(inventory.quantity_on_hand)
            restored_quantity = Decimal(item.quantity)
            next_quantity = old_quantity + restored_quantity
            restored_cost = Decimal(item.estimated_cost_rial or 0)
            current_cost = old_quantity * Decimal(inventory.weighted_average_cost_rial)
            inventory.quantity_on_hand = next_quantity
            inventory.weighted_average_cost_rial = (
                int(((current_cost + restored_cost) / next_quantity).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
                if next_quantity > 0
                else 0
            )
            db.add(
                InventoryTransaction(
                    variant_id=item.variant_id,
                    sale_invoice_id=invoice.id,
                    sale_invoice_item_id=item.id,
                    transaction_type="cancel_sale",
                    quantity_delta=restored_quantity,
                    unit_cost_rial=(
                        int((restored_cost / restored_quantity).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
                        if restored_quantity > 0
                        else None
                    ),
                    jalali_date=invoice.jalali_date,
                    local_time=invoice.local_time,
                    note=f"بازگشت موجودی از لغو فاکتور {invoice.invoice_number}",
                )
            )
        invoice.status = "canceled"
        invoice.is_active = False
        invoice.canceled_at_utc = utc_now()
        db.commit()
    return _get_invoice_or_404(db, invoice_id)


def get_daily_journal(db: Session, jalali_date: str) -> DailyJournalRead:
    invoices = list(
        db.scalars(
            select(SaleInvoice).where(
                SaleInvoice.jalali_date == jalali_date,
                SaleInvoice.status != "canceled",
                SaleInvoice.is_active.is_(True),
            )
        )
    )
    payments = list(
        db.scalars(
            select(Payment)
            .join(SaleInvoice)
            .where(
                Payment.jalali_date == jalali_date,
                SaleInvoice.status != "canceled",
                SaleInvoice.is_active.is_(True),
            )
        )
    )

    sales_total = sum(invoice.total_rial for invoice in invoices)
    received_total = sum(payment.amount_rial for payment in payments if payment.status == "received")
    pending_total = sum(payment.amount_rial for payment in payments if payment.status == "pending")
    invoice_ids = [invoice.id for invoice in invoices]
    estimated_profit_before_invoice_discount = sum(
        item.estimated_profit_rial or 0
        for item in db.scalars(select(SaleInvoiceItem).where(SaleInvoiceItem.invoice_id.in_(invoice_ids)))
    ) if invoice_ids else 0
    estimated_profit = estimated_profit_before_invoice_discount - sum(
        invoice.discount_amount_rial for invoice in invoices
    )
    breakdown: dict[str, dict[str, int]] = defaultdict(lambda: {"received": 0, "pending": 0})

    for payment in payments:
        breakdown[payment.method][payment.status] += payment.amount_rial

    return DailyJournalRead(
        jalali_date=jalali_date,
        invoice_count=len(invoices),
        sales_total_rial=sales_total,
        received_total_rial=received_total,
        pending_total_rial=pending_total,
        estimated_profit_rial=estimated_profit,
        payments=[
            DailyJournalPaymentBreakdown(
                method=method,
                received_rial=amounts["received"],
                pending_rial=amounts["pending"],
            )
            for method, amounts in sorted(breakdown.items())
        ],
    )
