from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.v1.auth import require_permission, require_superuser
from app.core.time import validate_jalali_date
from app.db.session import get_db
from app.models.user import User
from app.schemas.sales import (
    DailyJournalRead,
    PaymentDueAuditRead,
    PaymentDueDateUpdate,
    PaymentRead,
    SaleInvoiceCreate,
    SaleInvoiceRead,
    SalesFormOptionsRead,
)
from app.schemas.ledger import PersonAccountSummary
from app.services import sales as sales_service

router = APIRouter(dependencies=[Depends(require_permission("can_sales"))])


@router.post("/sales", response_model=SaleInvoiceRead, status_code=status.HTTP_201_CREATED)
def create_sale(
    payload: SaleInvoiceCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("can_sales")),
) -> SaleInvoiceRead:
    return sales_service.create_sale(db, payload, actor)


@router.get("/sales", response_model=list[SaleInvoiceRead])
def sales(db: Session = Depends(get_db)) -> list[SaleInvoiceRead]:
    return sales_service.list_sales(db)


@router.get("/sales/form-options", response_model=SalesFormOptionsRead)
def sales_form_options(db: Session = Depends(get_db)) -> SalesFormOptionsRead:
    return sales_service.get_sales_form_options(db)


@router.get("/sales/customers/{customer_id}/account-summary", response_model=PersonAccountSummary)
def customer_account_summary(customer_id: int, db: Session = Depends(get_db)) -> PersonAccountSummary:
    return sales_service.get_customer_account_summary(db, customer_id)


@router.get("/sales/{invoice_id}", response_model=SaleInvoiceRead)
def sale(invoice_id: int, db: Session = Depends(get_db)) -> SaleInvoiceRead:
    return sales_service.get_sale(db, invoice_id)


@router.patch("/sales/payments/{payment_id}/due-date", response_model=PaymentRead)
def update_payment_due_date(
    payment_id: int,
    payload: PaymentDueDateUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("can_sales")),
) -> PaymentRead:
    return sales_service.update_payment_due_date(db, payment_id, payload, actor)


@router.get("/sales/payments/{payment_id}/due-date/audits", response_model=list[PaymentDueAuditRead])
def payment_due_date_audits(
    payment_id: int,
    db: Session = Depends(get_db),
    _actor: User = Depends(require_permission("can_sales")),
) -> list[PaymentDueAuditRead]:
    return sales_service.list_payment_due_audits(db, payment_id)


@router.post("/sales/{invoice_id}/cancel", response_model=SaleInvoiceRead)
def cancel_sale(
    invoice_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_superuser),
) -> SaleInvoiceRead:
    return sales_service.cancel_sale(db, invoice_id, actor)


@router.get("/daily-journal", response_model=DailyJournalRead)
def daily_journal(
    jalali_date: str = Query(...),
    db: Session = Depends(get_db),
) -> DailyJournalRead:
    try:
        validated_date = validate_jalali_date(jalali_date)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return sales_service.get_daily_journal(db, validated_date)
