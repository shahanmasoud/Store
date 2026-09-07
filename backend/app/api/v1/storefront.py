from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.catalog import StorefrontCatalogItem
from app.services import storefront as storefront_service

router = APIRouter()


@router.get("/storefront/catalog", response_model=list[StorefrontCatalogItem])
def storefront_catalog(db: Session = Depends(get_db)) -> list[StorefrontCatalogItem]:
    return storefront_service.list_public_catalog(db)
