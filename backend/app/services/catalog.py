from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import Category, PriceList, PriceRule, Product, ProductVariant, Unit
from app.schemas.catalog import (
    CategoryCreate,
    PriceListCreate,
    PriceRuleCreate,
    ProductCreate,
    ProductVariantCreate,
    UnitCreate,
)


def list_units(db: Session) -> list[Unit]:
    return list(db.scalars(select(Unit).where(Unit.is_active.is_(True)).order_by(Unit.name)))


def create_unit(db: Session, payload: UnitCreate) -> Unit:
    unit = Unit(**payload.model_dump())
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


def list_categories(db: Session) -> list[Category]:
    return list(db.scalars(select(Category).where(Category.is_active.is_(True)).order_by(Category.name)))


def create_category(db: Session, payload: CategoryCreate) -> Category:
    category = Category(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def list_products(db: Session) -> list[Product]:
    return list(db.scalars(select(Product).where(Product.is_active.is_(True)).order_by(Product.name)))


def create_product(db: Session, payload: ProductCreate) -> Product:
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


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
