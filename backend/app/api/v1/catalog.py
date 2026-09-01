from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.db.session import get_db
from app.schemas.catalog import (
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
    PriceListCreate,
    PriceListRead,
    PriceRuleCreate,
    PriceRuleRead,
    ProductCreate,
    ProductRead,
    ProductVariantCreate,
    ProductVariantRead,
    UnitCreate,
    UnitRead,
)
from app.services import catalog as catalog_service

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/units", response_model=list[UnitRead])
def units(db: Session = Depends(get_db)) -> list[UnitRead]:
    return catalog_service.list_units(db)


@router.post("/units", response_model=UnitRead, status_code=status.HTTP_201_CREATED)
def create_unit(payload: UnitCreate, db: Session = Depends(get_db)) -> UnitRead:
    return catalog_service.create_unit(db, payload)


@router.get("/categories", response_model=list[CategoryRead])
def categories(db: Session = Depends(get_db)) -> list[CategoryRead]:
    return catalog_service.list_categories(db)


@router.post("/categories", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)) -> CategoryRead:
    return catalog_service.create_category(db, payload)


@router.patch("/categories/{category_id}", response_model=CategoryRead)
def update_category(category_id: int, payload: CategoryUpdate, db: Session = Depends(get_db)) -> CategoryRead:
    return catalog_service.update_category(db, category_id, payload)


@router.delete("/categories/{category_id}", response_model=CategoryRead)
def deactivate_category(category_id: int, db: Session = Depends(get_db)) -> CategoryRead:
    return catalog_service.deactivate_category(db, category_id)


@router.get("/products", response_model=list[ProductRead])
def products(db: Session = Depends(get_db)) -> list[ProductRead]:
    return catalog_service.list_products(db)


@router.post("/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)) -> ProductRead:
    return catalog_service.create_product(db, payload)


@router.get("/product-variants", response_model=list[ProductVariantRead])
def variants(db: Session = Depends(get_db)) -> list[ProductVariantRead]:
    return catalog_service.list_variants(db)


@router.post("/product-variants", response_model=ProductVariantRead, status_code=status.HTTP_201_CREATED)
def create_variant(payload: ProductVariantCreate, db: Session = Depends(get_db)) -> ProductVariantRead:
    return catalog_service.create_variant(db, payload)


@router.post("/prices", response_model=PriceListRead, status_code=status.HTTP_201_CREATED)
def create_price(payload: PriceListCreate, db: Session = Depends(get_db)) -> PriceListRead:
    return catalog_service.create_price(db, payload)


@router.post("/price-rules", response_model=PriceRuleRead, status_code=status.HTTP_201_CREATED)
def create_price_rule(payload: PriceRuleCreate, db: Session = Depends(get_db)) -> PriceRuleRead:
    return catalog_service.create_price_rule(db, payload)
