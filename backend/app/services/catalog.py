from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.catalog import Category, PriceList, PriceRule, Product, ProductVariant, Unit
from app.schemas.catalog import (
    CategoryCreate,
    CategoryUpdate,
    PriceListCreate,
    PriceRuleCreate,
    ProductCreate,
    ProductUpdate,
    ProductVariantCreate,
    UnitCreate,
    UnitUpdate,
)


def list_units(db: Session) -> list[Unit]:
    return list(db.scalars(select(Unit).where(Unit.is_active.is_(True)).order_by(Unit.name)))


def _get_unit(db: Session, unit_id: int) -> Unit:
    unit = db.get(Unit, unit_id)
    if unit is None or not unit.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="واحد فعال پیدا نشد.")
    return unit


def _ensure_unique_unit(db: Session, name: str, symbol: str, *, exclude_id: int | None = None) -> None:
    active_units = db.scalars(select(Unit).where(Unit.is_active.is_(True)))
    for unit in active_units:
        if unit.id == exclude_id:
            continue
        if unit.name.strip().casefold() == name.casefold():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="واحدی با این نام وجود دارد.")
        if unit.symbol.strip().casefold() == symbol.casefold():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="واحدی با این نماد وجود دارد.")


def _commit_catalog_record(db: Session, record: Unit | Category | Product, entity_name: str):
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"ثبت {entity_name} به‌دلیل تداخل با اطلاعات موجود انجام نشد.",
        ) from exc
    db.refresh(record)
    return record


def create_unit(db: Session, payload: UnitCreate) -> Unit:
    _ensure_unique_unit(db, payload.name, payload.symbol)
    unit = Unit(**payload.model_dump())
    db.add(unit)
    return _commit_catalog_record(db, unit, "واحد")


def update_unit(db: Session, unit_id: int, payload: UnitUpdate) -> Unit:
    unit = _get_unit(db, unit_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="حداقل یک تغییر وارد کنید.")
    name = changes.get("name", unit.name)
    symbol = changes.get("symbol", unit.symbol)
    _ensure_unique_unit(db, name, symbol, exclude_id=unit.id)
    unit.name = name
    unit.symbol = symbol
    return _commit_catalog_record(db, unit, "واحد")


def deactivate_unit(db: Session, unit_id: int) -> Unit:
    unit = _get_unit(db, unit_id)
    has_active_variant = db.scalar(
        select(ProductVariant.id).where(ProductVariant.unit_id == unit.id, ProductVariant.is_active.is_(True)).limit(1)
    )
    if has_active_variant is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="این واحد در گونه کالای فعال استفاده شده است؛ ابتدا گونه‌های مرتبط را تغییر دهید یا غیرفعال کنید.",
        )
    unit.is_active = False
    return _commit_catalog_record(db, unit, "واحد")


def list_categories(db: Session) -> list[Category]:
    return list(db.scalars(select(Category).where(Category.is_active.is_(True)).order_by(Category.name)))


def _get_category(db: Session, category_id: int) -> Category:
    category = db.get(Category, category_id)
    if category is None or not category.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="دسته فعال پیدا نشد.")
    return category


def _validate_parent(db: Session, parent_id: int | None, *, category_id: int | None = None) -> None:
    if parent_id is None:
        return
    if category_id is not None and parent_id == category_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="یک دسته نمی‌تواند والد خودش باشد.")

    parent = _get_category(db, parent_id)
    visited: set[int] = set()
    while parent is not None:
        if parent.id in visited:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="ساختار دسته‌بندی دارای چرخه است.")
        if category_id is not None and parent.id == category_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="انتخاب این والد باعث ایجاد چرخه در دسته‌بندی می‌شود.")
        visited.add(parent.id)
        parent = parent.parent


def _ensure_unique_sibling_name(
    db: Session,
    name: str,
    parent_id: int | None,
    *,
    exclude_id: int | None = None,
) -> None:
    siblings = db.scalars(select(Category).where(Category.parent_id == parent_id, Category.is_active.is_(True)))
    if any(sibling.id != exclude_id and sibling.name.strip().casefold() == name.casefold() for sibling in siblings):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="دسته‌ای با این نام در همین سطح وجود دارد.",
        )


def _commit_category(db: Session, category: Category) -> Category:
    return _commit_catalog_record(db, category, "دسته")


def create_category(db: Session, payload: CategoryCreate) -> Category:
    _validate_parent(db, payload.parent_id)
    _ensure_unique_sibling_name(db, payload.name, payload.parent_id)
    category = Category(**payload.model_dump())
    db.add(category)
    return _commit_category(db, category)


def update_category(db: Session, category_id: int, payload: CategoryUpdate) -> Category:
    category = _get_category(db, category_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="حداقل یک تغییر وارد کنید.")

    name = changes.get("name", category.name)
    parent_id = changes.get("parent_id", category.parent_id)
    _validate_parent(db, parent_id, category_id=category.id)
    _ensure_unique_sibling_name(db, name, parent_id, exclude_id=category.id)
    category.name = name
    category.parent_id = parent_id
    return _commit_category(db, category)


def deactivate_category(db: Session, category_id: int) -> Category:
    category = _get_category(db, category_id)
    has_active_child = db.scalar(
        select(Category.id).where(Category.parent_id == category.id, Category.is_active.is_(True)).limit(1)
    )
    if has_active_child is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="این دسته فرزند فعال دارد؛ ابتدا دسته‌های زیرمجموعه را جابه‌جا یا غیرفعال کنید.",
        )
    has_active_product = db.scalar(
        select(Product.id).where(Product.category_id == category.id, Product.is_active.is_(True)).limit(1)
    )
    if has_active_product is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="این دسته کالای فعال دارد؛ ابتدا کالاها را جابه‌جا یا غیرفعال کنید.",
        )
    category.is_active = False
    return _commit_category(db, category)


def list_products(db: Session) -> list[Product]:
    return list(db.scalars(select(Product).where(Product.is_active.is_(True)).order_by(Product.name)))


def _get_product(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="کالای فعال پیدا نشد.")
    return product


def _validate_product_category(db: Session, category_id: int | None) -> None:
    if category_id is not None:
        _get_category(db, category_id)


def _ensure_unique_product_name(
    db: Session,
    name: str,
    category_id: int | None,
    *,
    exclude_id: int | None = None,
) -> None:
    products = db.scalars(select(Product).where(Product.category_id == category_id, Product.is_active.is_(True)))
    if any(product.id != exclude_id and product.name.strip().casefold() == name.casefold() for product in products):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="کالایی با این نام در همین دسته وجود دارد.",
        )


def create_product(db: Session, payload: ProductCreate) -> Product:
    _validate_product_category(db, payload.category_id)
    _ensure_unique_product_name(db, payload.name, payload.category_id)
    product = Product(**payload.model_dump())
    db.add(product)
    return _commit_catalog_record(db, product, "کالا")


def update_product(db: Session, product_id: int, payload: ProductUpdate) -> Product:
    product = _get_product(db, product_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="حداقل یک تغییر وارد کنید.")
    name = changes.get("name", product.name)
    category_id = changes.get("category_id", product.category_id)
    _validate_product_category(db, category_id)
    _ensure_unique_product_name(db, name, category_id, exclude_id=product.id)
    for field, value in changes.items():
        setattr(product, field, value)
    return _commit_catalog_record(db, product, "کالا")


def deactivate_product(db: Session, product_id: int) -> Product:
    product = _get_product(db, product_id)
    has_active_variant = db.scalar(
        select(ProductVariant.id).where(
            ProductVariant.product_id == product.id,
            ProductVariant.is_active.is_(True),
        ).limit(1)
    )
    if has_active_variant is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="این کالا گونه فعال دارد؛ ابتدا گونه‌های مرتبط را غیرفعال کنید.",
        )
    product.is_active = False
    return _commit_catalog_record(db, product, "کالا")


def list_variants(db: Session) -> list[ProductVariant]:
    return list(db.scalars(select(ProductVariant).where(ProductVariant.is_active.is_(True)).order_by(ProductVariant.name)))


def create_variant(db: Session, payload: ProductVariantCreate) -> ProductVariant:
    variant = ProductVariant(**payload.model_dump())
    db.add(variant)
    db.commit()
    db.refresh(variant)
    return variant


def create_price(db: Session, payload: PriceListCreate) -> PriceList:
    price = PriceList(**payload.model_dump())
    db.add(price)
    db.commit()
    db.refresh(price)
    return price


def create_price_rule(db: Session, payload: PriceRuleCreate) -> PriceRule:
    rule = PriceRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule
