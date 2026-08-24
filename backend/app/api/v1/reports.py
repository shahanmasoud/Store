from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.time import validate_jalali_date
from app.db.session import get_db
from app.schemas.reports import (
    CashflowReportRead,
    CustomerDebtReportRead,
    InventoryReportRead,
    ProfitLossRead,
    SalesSummaryRead,
)
from app.services import reports as report_service

router = APIRouter(dependencies=[Depends(get_current_user)])


def _valid_date(value: str) -> str:
    try:
        return validate_jalali_date(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _valid_date_range(from_jalali: str, to_jalali: str) -> tuple[str, str]:
    valid_from = _valid_date(from_jalali)
    valid_to = _valid_date(to_jalali)
    if valid_from > valid_to:
        raise HTTPException(status_code=422, detail="تاریخ شروع نباید بعد از تاریخ پایان باشد.")
    return valid_from, valid_to


@router.get("/reports/sales-summary", response_model=SalesSummaryRead)
def sales_summary(
    from_jalali: str = Query(...),
    to_jalali: str = Query(...),
    db: Session = Depends(get_db),
) -> SalesSummaryRead:
    valid_from, valid_to = _valid_date_range(from_jalali, to_jalali)
    return report_service.sales_summary(db, valid_from, valid_to)


@router.get("/reports/profit-loss", response_model=ProfitLossRead)
def profit_loss(
    from_jalali: str = Query(...),
    to_jalali: str = Query(...),
    db: Session = Depends(get_db),
) -> ProfitLossRead:
    valid_from, valid_to = _valid_date_range(from_jalali, to_jalali)
    return report_service.profit_loss(db, valid_from, valid_to)


@router.get("/reports/inventory", response_model=InventoryReportRead)
def inventory(db: Session = Depends(get_db)) -> InventoryReportRead:
    return report_service.inventory_report(db)


@router.get("/reports/cashflow", response_model=CashflowReportRead)
def cashflow(jalali_date_to: str = Query(...), db: Session = Depends(get_db)) -> CashflowReportRead:
    return report_service.cashflow_report(db, _valid_date(jalali_date_to))


@router.get("/reports/customer-debts", response_model=CustomerDebtReportRead)
def customer_debts(db: Session = Depends(get_db)) -> CustomerDebtReportRead:
    return report_service.customer_debts(db)
