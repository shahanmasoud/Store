from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.time import utc_now
from app.models.catalog import ProductVariant
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
            detail=f"Product variant not found or inactive: {sorted(missing_ids)}",
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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invoice total cannot be negative.")

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
        db.add(
            SaleInvoiceItem(
                invoice_id=invoice.id,
                variant_id=item.variant_id,
                quantity=item.quantity,
                unit_price_rial=item.unit_price_rial,
                discount_amount_rial=item.discount_amount_rial,
                line_total_rial=_line_total(item.quantity, item.unit_price_rial, item.discount_amount_rial),
                estimated_cost_rial=item.estimated_cost_rial,
                estimated_profit_rial=(
                    _line_total(item.quantity, item.unit_price_rial, item.discount_amount_rial) - item.estimated_cost_rial
                    if item.estimated_cost_rial is not None
                    else None
                ),
                product_snapshot=variant.name,
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
    breakdown: dict[str, dict[str, int]] = defaultdict(lambda: {"received": 0, "pending": 0})

    for payment in payments:
        breakdown[payment.method][payment.status] += payment.amount_rial

    return DailyJournalRead(
        jalali_date=jalali_date,
        invoice_count=len(invoices),
        sales_total_rial=sales_total,
        received_total_rial=received_total,
        pending_total_rial=pending_total,
        payments=[
            DailyJournalPaymentBreakdown(
                method=method,
                received_rial=amounts["received"],
                pending_rial=amounts["pending"],
            )
            for method, amounts in sorted(breakdown.items())
        ],
    )
