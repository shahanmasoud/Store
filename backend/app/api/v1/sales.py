from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.time import validate_jalali_date
from app.db.session import get_db
from app.schemas.sales import DailyJournalRead, SaleInvoiceCreate, SaleInvoiceRead
from app.services import sales as sales_service

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.post("/sales", response_model=SaleInvoiceRead, status_code=status.HTTP_201_CREATED)
def create_sale(payload: SaleInvoiceCreate, db: Session = Depends(get_db)) -> SaleInvoiceRead:
    return sales_service.create_sale(db, payload)


@router.get("/sales", response_model=list[SaleInvoiceRead])
def sales(db: Session = Depends(get_db)) -> list[SaleInvoiceRead]:
    return sales_service.list_sales(db)


@router.get("/sales/{invoice_id}", response_model=SaleInvoiceRead)
def sale(invoice_id: int, db: Session = Depends(get_db)) -> SaleInvoiceRead:
    return sales_service.get_sale(db, invoice_id)


@router.post("/sales/{invoice_id}/cancel", response_model=SaleInvoiceRead)
def cancel_sale(invoice_id: int, db: Session = Depends(get_db)) -> SaleInvoiceRead:
    return sales_service.cancel_sale(db, invoice_id)


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
