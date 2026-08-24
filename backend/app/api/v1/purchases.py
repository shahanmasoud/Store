from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.db.session import get_db
from app.schemas.purchases import InventoryRead, PurchaseInvoiceCreate, PurchaseInvoiceRead
from app.services import purchases as purchase_service

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.post("/purchase-invoices", response_model=PurchaseInvoiceRead, status_code=status.HTTP_201_CREATED)
def create_purchase(payload: PurchaseInvoiceCreate, db: Session = Depends(get_db)) -> PurchaseInvoiceRead:
    return purchase_service.create_purchase(db, payload)


@router.get("/purchase-invoices", response_model=list[PurchaseInvoiceRead])
def purchases(db: Session = Depends(get_db)) -> list[PurchaseInvoiceRead]:
    return purchase_service.list_purchases(db)


@router.get("/purchase-invoices/{invoice_id}", response_model=PurchaseInvoiceRead)
def purchase(invoice_id: int, db: Session = Depends(get_db)) -> PurchaseInvoiceRead:
    return purchase_service.get_purchase(db, invoice_id)


@router.post("/purchase-invoices/{invoice_id}/cancel", response_model=PurchaseInvoiceRead)
def cancel_purchase(invoice_id: int, db: Session = Depends(get_db)) -> PurchaseInvoiceRead:
    return purchase_service.cancel_purchase(db, invoice_id)


@router.get("/inventory", response_model=list[InventoryRead])
def inventory(db: Session = Depends(get_db)) -> list[InventoryRead]:
    return purchase_service.list_inventory(db)
