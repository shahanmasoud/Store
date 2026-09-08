from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.v1.auth import require_permission, require_superuser
from app.db.session import get_db
from app.schemas.purchases import (
    InventoryAdjustmentCreate,
    InventoryRead,
    InventoryTransactionRead,
    InventoryUpdate,
    PurchaseInvoiceCreate,
    PurchaseInvoiceRead,
)
from app.models.user import User
from app.services import purchases as purchase_service

router = APIRouter(dependencies=[Depends(require_permission("can_catalog_inventory"))])


@router.post("/purchase-invoices", response_model=PurchaseInvoiceRead, status_code=status.HTTP_201_CREATED)
def create_purchase(payload: PurchaseInvoiceCreate, db: Session = Depends(get_db)) -> PurchaseInvoiceRead:
    return purchase_service.create_purchase(db, payload)


@router.get("/purchase-invoices", response_model=list[PurchaseInvoiceRead])
def purchases(db: Session = Depends(get_db)) -> list[PurchaseInvoiceRead]:
    return purchase_service.list_purchases(db)


@router.get("/purchase-invoices/{invoice_id}", response_model=PurchaseInvoiceRead)
def purchase(invoice_id: int, db: Session = Depends(get_db)) -> PurchaseInvoiceRead:
    return purchase_service.get_purchase(db, invoice_id)


@router.post("/purchase-invoices/{invoice_id}/cancel", response_model=PurchaseInvoiceRead, dependencies=[Depends(require_superuser)])
def cancel_purchase(invoice_id: int, db: Session = Depends(get_db)) -> PurchaseInvoiceRead:
    return purchase_service.cancel_purchase(db, invoice_id)


@router.get("/inventory", response_model=list[InventoryRead])
def inventory(db: Session = Depends(get_db)) -> list[InventoryRead]:
    return purchase_service.list_inventory(db)


@router.patch("/inventory/{inventory_id}", response_model=InventoryRead)
def update_inventory(
    inventory_id: int,
    payload: InventoryUpdate,
    db: Session = Depends(get_db),
) -> InventoryRead:
    return purchase_service.update_inventory(db, inventory_id, payload)


@router.post("/inventory/adjustments", response_model=InventoryTransactionRead, status_code=status.HTTP_201_CREATED)
def create_inventory_adjustment(
    payload: InventoryAdjustmentCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("can_catalog_inventory")),
) -> InventoryTransactionRead:
    return purchase_service.create_inventory_adjustment(db, payload, actor=actor)


@router.get("/inventory-transactions", response_model=list[InventoryTransactionRead])
def inventory_transactions(
    variant_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[InventoryTransactionRead]:
    return purchase_service.list_inventory_transactions(db, variant_id=variant_id, limit=limit)
