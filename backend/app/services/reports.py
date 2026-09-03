from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.catalog import ProductVariant
from app.models.ledger import Cheque, LedgerEntry, Person
from app.models.purchases import InventoryItem
from app.models.sales import Payment, SaleInvoice, SaleInvoiceItem
from app.schemas.reports import (
    CashflowReportRead,
    CustomerDebtReportRead,
    CustomerDebtRowRead,
    InventoryReportRead,
    InventoryRowRead,
    ProfitLossRead,
    SalesSummaryRead,
)


def sales_summary(db: Session, from_jalali: str, to_jalali: str) -> SalesSummaryRead:
    invoices = list(
        db.scalars(
            select(SaleInvoice).where(
                SaleInvoice.jalali_date >= from_jalali,
                SaleInvoice.jalali_date <= to_jalali,
                SaleInvoice.status != "canceled",
                SaleInvoice.is_active.is_(True),
            )
        )
    )
    invoice_ids = [invoice.id for invoice in invoices]
    payments = []
    if invoice_ids:
        payments = list(
            db.scalars(
                select(Payment).where(
                    Payment.invoice_id.in_(invoice_ids),
                    Payment.jalali_date >= from_jalali,
                    Payment.jalali_date <= to_jalali,
                )
            )
        )
    registered_sales = sum(invoice.total_rial for invoice in invoices)
    received = sum(payment.amount_rial for payment in payments if payment.status == "received")
    pending = sum(payment.amount_rial for payment in payments if payment.status == "pending")
    average = round(registered_sales / len(invoices)) if invoices else 0
    return SalesSummaryRead(
        from_jalali=from_jalali,
        to_jalali=to_jalali,
        invoice_count=len(invoices),
        registered_sales_rial=registered_sales,
        received_rial=received,
        pending_rial=pending,
        average_invoice_rial=average,
    )


def profit_loss(db: Session, from_jalali: str, to_jalali: str) -> ProfitLossRead:
    invoices = list(
        db.scalars(
            select(SaleInvoice).where(
                SaleInvoice.jalali_date >= from_jalali,
                SaleInvoice.jalali_date <= to_jalali,
                SaleInvoice.status != "canceled",
                SaleInvoice.is_active.is_(True),
            )
        )
    )
    invoice_ids = [invoice.id for invoice in invoices]
    items = []
    if invoice_ids:
        items = list(
            db.scalars(
                select(SaleInvoiceItem).where(SaleInvoiceItem.invoice_id.in_(invoice_ids))
            )
        )
    sales = sum(invoice.total_rial for invoice in invoices)
    estimated_cost = sum(item.estimated_cost_rial or 0 for item in items)
    gross_profit = sales - estimated_cost
    margin = round((gross_profit / sales) * 100, 2) if sales else 0
    return ProfitLossRead(
        from_jalali=from_jalali,
        to_jalali=to_jalali,
        sales_rial=sales,
        estimated_cost_rial=estimated_cost,
        gross_profit_rial=gross_profit,
        gross_margin_percent=margin,
    )


def _ledger_components(db: Session, jalali_date_to: str) -> tuple[int, int]:
    rows = db.execute(
        select(Person, LedgerEntry).join(LedgerEntry, LedgerEntry.person_id == Person.id).where(
            LedgerEntry.status == "open",
            LedgerEntry.remaining_rial > 0,
            LedgerEntry.jalali_date <= jalali_date_to,
            LedgerEntry.is_active.is_(True),
            Person.is_active.is_(True),
        )
    ).all()
    balances: dict[int, int] = {}
    people: dict[int, Person] = {}
    for person, entry in rows:
        people[person.id] = person
        direction = 1 if entry.entry_type == "debit" else -1
        balances[person.id] = balances.get(person.id, 0) + (direction * entry.remaining_rial)
    customer_receivables = sum(
        max(balance, 0)
        for person_id, balance in balances.items()
        if people[person_id].person_type in {"customer", "both"}
    )
    supplier_payables = sum(
        max(-balance, 0)
        for person_id, balance in balances.items()
        if people[person_id].person_type in {"supplier", "both"}
    )
    return customer_receivables, supplier_payables


def inventory_report(db: Session) -> InventoryReportRead:
    rows = db.execute(
        select(InventoryItem, ProductVariant)
        .join(ProductVariant, ProductVariant.id == InventoryItem.variant_id)
        .order_by(ProductVariant.name)
    ).all()
    items = []
    for inventory, variant in rows:
        quantity = Decimal(inventory.quantity_on_hand)
        estimated_value = int(quantity * Decimal(inventory.weighted_average_cost_rial))
        needs_reorder = inventory.reorder_level is not None and quantity <= Decimal(inventory.reorder_level)
        items.append(
            InventoryRowRead(
                variant_id=inventory.variant_id,
                variant_name=variant.name,
                quantity_on_hand=inventory.quantity_on_hand,
                weighted_average_cost_rial=inventory.weighted_average_cost_rial,
                estimated_value_rial=estimated_value,
                reorder_level=inventory.reorder_level,
                needs_reorder=needs_reorder,
            )
        )
    return InventoryReportRead(
        item_count=len(items),
        total_value_rial=sum(item.estimated_value_rial for item in items),
        low_stock_count=sum(1 for item in items if item.needs_reorder),
        items=items,
    )


def cashflow_report(db: Session, jalali_date_to: str) -> CashflowReportRead:
    pending_sales = sum(
        db.scalars(
            select(Payment.amount_rial)
            .join(SaleInvoice)
            .where(
                Payment.status == "pending",
                Payment.due_jalali_date <= jalali_date_to,
                SaleInvoice.status != "canceled",
                SaleInvoice.is_active.is_(True),
            )
        )
    )
    active_invoices = list(
        db.scalars(
            select(SaleInvoice).where(
                SaleInvoice.jalali_date <= jalali_date_to,
                SaleInvoice.status != "canceled",
                SaleInvoice.is_active.is_(True),
            )
        )
    )
    active_invoice_ids = [invoice.id for invoice in active_invoices]
    assigned_pending_by_invoice: dict[int, int] = {}
    if active_invoice_ids:
        for invoice_id, amount in db.execute(
            select(Payment.invoice_id, func.coalesce(func.sum(Payment.amount_rial), 0))
            .where(
                Payment.invoice_id.in_(active_invoice_ids),
                Payment.status == "pending",
                Payment.due_jalali_date.is_not(None),
            )
            .group_by(Payment.invoice_id)
        ):
            assigned_pending_by_invoice[invoice_id] = int(amount)
    unallocated_sales_due = sum(
        max(invoice.due_total_rial - assigned_pending_by_invoice.get(invoice.id, 0), 0)
        for invoice in active_invoices
    )
    customer_receivables, supplier_payables = _ledger_components(db, jalali_date_to)
    open_ledger = customer_receivables - supplier_payables
    received_cheques = sum(
        db.scalars(
            select(Cheque.amount_rial).where(
                Cheque.cheque_type == "received",
                Cheque.status == "pending",
                Cheque.due_jalali_date <= jalali_date_to,
                Cheque.is_active.is_(True),
            )
        )
    )
    paid_cheques = sum(
        db.scalars(
            select(Cheque.amount_rial).where(
                Cheque.cheque_type == "paid",
                Cheque.status == "pending",
                Cheque.due_jalali_date <= jalali_date_to,
                Cheque.is_active.is_(True),
            )
        )
    )
    return CashflowReportRead(
        jalali_date_to=jalali_date_to,
        pending_sales_payments_rial=pending_sales,
        unallocated_sales_due_rial=unallocated_sales_due,
        total_sales_receivables_rial=pending_sales + unallocated_sales_due,
        open_customer_receivables_rial=customer_receivables,
        open_supplier_payables_rial=supplier_payables,
        open_ledger_rial=open_ledger,
        pending_received_cheques_rial=received_cheques,
        pending_paid_cheques_rial=paid_cheques,
        net_expected_rial=(
            pending_sales
            + unallocated_sales_due
            + customer_receivables
            + received_cheques
            - supplier_payables
            - paid_cheques
        ),
    )


def customer_debts(db: Session) -> CustomerDebtReportRead:
    rows = db.execute(
        select(Person, LedgerEntry)
        .join(LedgerEntry, LedgerEntry.person_id == Person.id)
        .where(
            LedgerEntry.status == "open",
            LedgerEntry.remaining_rial > 0,
            LedgerEntry.is_active.is_(True),
            Person.is_active.is_(True),
            Person.person_type.in_(["customer", "both"]),
        )
        .order_by(Person.name)
    ).all()
    totals: dict[int, CustomerDebtRowRead] = {}
    for person, entry in rows:
        direction = 1 if entry.entry_type == "debit" else -1
        current = totals.get(person.id)
        next_remaining = (current.remaining_rial if current else 0) + (direction * entry.remaining_rial)
        totals[person.id] = CustomerDebtRowRead(
            person_id=person.id,
            person_name=person.name,
            remaining_rial=next_remaining,
        )
    people = [
        person.model_copy(update={"remaining_rial": max(person.remaining_rial, 0)})
        for person in totals.values()
        if person.remaining_rial > 0
    ]
    return CustomerDebtReportRead(
        total_remaining_rial=sum(person.remaining_rial for person in people),
        people=people,
    )
