from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import exists, select, update
from sqlalchemy.orm import Session, selectinload

from app.core.time import utc_now
from app.models.catalog import ProductVariant
from app.models.purchases import InventoryItem, InventoryTransaction
from app.models.ledger import LedgerActionAudit, LedgerEntry, Person
from app.models.sales import Payment, PaymentDueAudit, SaleInvoice, SaleInvoiceItem
from app.models.user import User
from app.schemas.sales import DailyJournalPaymentBreakdown, DailyJournalRead, PaymentCreate, PaymentDueDateUpdate, SaleInvoiceCreate
from app.schemas.sales import SalesFormOptionsRead
from app.services import catalog as catalog_service
from app.services import ledger as ledger_service
from app.services import purchases as purchase_service

RECEIVED_BY_DEFAULT = {"cash", "card", "transfer"}


def get_sales_form_options(db: Session) -> SalesFormOptionsRead:
    return SalesFormOptionsRead(
        variants=catalog_service.list_variants(db),
        inventory=purchase_service.list_inventory(db),
        customers=[
            person
            for person in ledger_service.list_persons(db)
            if person.person_type in {"customer", "both"}
        ],
    )


def get_customer_account_summary(db: Session, customer_id: int) -> dict[str, int]:
    customer = db.get(Person, customer_id)
    if customer is None or not customer.is_active or customer.person_type not in {"customer", "both"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="مشتری فعال پیدا نشد.")
    return ledger_service.get_person_account_summary(db, customer_id)


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


def _normalized_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _get_payment_or_404(db: Session, payment_id: int) -> Payment:
    payment = db.scalar(
        select(Payment).options(selectinload(Payment.invoice)).where(Payment.id == payment_id)
    )
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="پرداخت فروش پیدا نشد.")
    return payment


def update_payment_due_date(
    db: Session,
    payment_id: int,
    payload: PaymentDueDateUpdate,
    actor: User,
) -> Payment:
    payment = _get_payment_or_404(db, payment_id)
    if payment.status != "pending" or payment.invoice.status != "active" or not payment.invoice.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="فقط سررسید پرداخت بازِ فاکتور فعال قابل تغییر است.",
        )
    if payment.updated_at_utc is None or _normalized_utc(payment.updated_at_utc) != _normalized_utc(payload.expected_updated_at):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="این پرداخت پس از باز شدن فرم تغییر کرده است؛ اطلاعات را دوباره دریافت کنید.",
        )
    if payment.due_jalali_date == payload.due_jalali_date:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="سررسید جدید با مقدار فعلی یکسان است.")

    before_due_date = payment.due_jalali_date
    next_updated_at = utc_now()
    result = db.execute(
        update(Payment)
        .where(
            Payment.id == payment.id,
            Payment.status == "pending",
            Payment.updated_at_utc == payload.expected_updated_at,
            exists().where(
                SaleInvoice.id == Payment.invoice_id,
                SaleInvoice.status == "active",
                SaleInvoice.is_active.is_(True),
            ),
        )
        .values(due_jalali_date=payload.due_jalali_date, updated_at_utc=next_updated_at)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        db.rollback()
        db.expire_all()
        current = _get_payment_or_404(db, payment_id)
        if current.status != "pending" or current.invoice.status != "active" or not current.invoice.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="فقط سررسید پرداخت بازِ فاکتور فعال قابل تغییر است.",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="این پرداخت پس از باز شدن فرم تغییر کرده است؛ اطلاعات را دوباره دریافت کنید.",
        )
    db.add(
        PaymentDueAudit(
            payment_id=payment.id,
            actor_user_id=actor.id,
            actor_username=actor.username,
            actor_full_name=actor.full_name,
            before_due_date=before_due_date,
            after_due_date=payload.due_jalali_date,
            reason=payload.reason,
        )
    )
    db.commit()
    return _get_payment_or_404(db, payment.id)


def list_payment_due_audits(db: Session, payment_id: int) -> list[PaymentDueAudit]:
    _get_payment_or_404(db, payment_id)
    return list(
        db.scalars(
            select(PaymentDueAudit)
            .where(PaymentDueAudit.payment_id == payment_id)
            .order_by(PaymentDueAudit.occurred_at_utc, PaymentDueAudit.id)
        )
    )


def _get_invoice_or_404(db: Session, invoice_id: int) -> SaleInvoice:
    invoice = db.scalar(
        select(SaleInvoice)
        .options(selectinload(SaleInvoice.items), selectinload(SaleInvoice.payments))
        .where(SaleInvoice.id == invoice_id)
    )
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sale invoice not found.")
    return invoice


def _audit_sale_action(
    db: Session,
    *,
    entity_type: str,
    entity_id: int,
    action: str,
    actor: User | None,
    before: dict | None,
    after: dict | None,
) -> None:
    if actor is None:
        return
    db.add(
        LedgerActionAudit(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor_user_id=actor.id,
            actor_username=actor.username,
            actor_full_name=actor.full_name,
            before_json=before,
            after_json=after,
            reason="ثبت فروش" if action == "create" else "لغو فروش",
        )
    )


def create_sale(db: Session, payload: SaleInvoiceCreate, actor: User | None = None) -> SaleInvoice:
    customer_name = payload.customer_name
    if payload.customer_id is not None:
        customer = db.get(Person, payload.customer_id)
        if customer is None or not customer.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="مشتری فعال پیدا نشد.",
            )
        if customer.person_type not in {"customer", "both"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="شخص انتخاب‌شده مشتری نیست و نمی‌تواند به فاکتور فروش متصل شود.",
            )
        # The stored name is an immutable invoice-time snapshot of the canonical person name.
        customer_name = customer.name

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
        customer_id=payload.customer_id,
        customer_name=customer_name,
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

    payment_updated_at = utc_now()
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
                updated_at_utc=payment_updated_at,
            )
        )

    if invoice.customer_id is not None and due_total > 0:
        pending_due_dates = [
            payment.due_jalali_date
            for payment in payload.payments
            if _default_payment_status(payment) == "pending" and payment.due_jalali_date is not None
        ]
        entry = LedgerEntry(
            person_id=invoice.customer_id,
            entry_type="debit",
            amount_rial=due_total,
            remaining_rial=due_total,
            source_type="sale",
            source_id=invoice.id,
            jalali_date=invoice.jalali_date,
            due_jalali_date=min(pending_due_dates) if pending_due_dates else None,
            local_time=invoice.local_time,
            description=f"مطالبه فاکتور {invoice.invoice_number}",
        )
        db.add(entry)
        db.flush()
        _audit_sale_action(
            db,
            entity_type="ledger_entry",
            entity_id=entry.id,
            action="create",
            actor=actor,
            before=None,
            after={
                "id": entry.id,
                "person_id": entry.person_id,
                "amount_rial": entry.amount_rial,
                "remaining_rial": entry.remaining_rial,
                "source_type": entry.source_type,
                "source_id": entry.source_id,
                "status": entry.status,
                "is_active": entry.is_active,
            },
        )
    _audit_sale_action(
        db,
        entity_type="sale_invoice",
        entity_id=invoice.id,
        action="create",
        actor=actor,
        before=None,
        after={"id": invoice.id, "customer_id": invoice.customer_id, "total_rial": total, "due_total_rial": due_total},
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


def cancel_sale(db: Session, invoice_id: int, actor: User | None = None) -> SaleInvoice:
    invoice = _get_invoice_or_404(db, invoice_id)
    if invoice.status != "canceled":
        sale_entry = db.scalar(
            select(LedgerEntry).where(
                LedgerEntry.source_type == "sale",
                LedgerEntry.source_id == invoice.id,
            )
        )
        if sale_entry is not None and (
            not sale_entry.is_active
            or sale_entry.status != "open"
            or sale_entry.remaining_rial != sale_entry.amount_rial
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="فاکتور دارای تسویه ثبت‌شده است و قابل لغو نیست.",
            )
        before = {
            "id": invoice.id,
            "status": invoice.status,
            "is_active": invoice.is_active,
            "due_total_rial": invoice.due_total_rial,
        }
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
        if sale_entry is not None:
            entry_before = {
                "remaining_rial": sale_entry.remaining_rial,
                "status": sale_entry.status,
                "is_active": sale_entry.is_active,
            }
            sale_entry.remaining_rial = 0
            sale_entry.status = "canceled"
            sale_entry.is_active = False
            _audit_sale_action(
                db,
                entity_type="ledger_entry",
                entity_id=sale_entry.id,
                action="cancel",
                actor=actor,
                before=entry_before,
                after={"remaining_rial": 0, "status": "canceled", "is_active": False},
            )
        _audit_sale_action(
            db,
            entity_type="sale_invoice",
            entity_id=invoice.id,
            action="cancel",
            actor=actor,
            before=before,
            after={"id": invoice.id, "status": "canceled", "is_active": False, "due_total_rial": invoice.due_total_rial},
        )
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
