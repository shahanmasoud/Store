from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.catalog import Category, Product, ProductVariant, Unit
from app.models.purchases import InventoryItem
from app.models.online import StockReservation
from app.core.time import current_jalali_date
from app.schemas.catalog import StorefrontCatalogItem


def list_public_catalog(db: Session) -> list[StorefrontCatalogItem]:
    today = current_jalali_date()
    active_reservations = (
        select(
            StockReservation.variant_id.label("variant_id"),
            func.sum(StockReservation.quantity).label("reserved_quantity"),
        )
        .where(
            StockReservation.status == "reserved",
            StockReservation.is_active.is_(True),
            (StockReservation.expires_jalali_date.is_(None))
            | (StockReservation.expires_jalali_date >= today),
        )
        .group_by(StockReservation.variant_id)
        .subquery()
    )
    rows = db.execute(
        select(
            ProductVariant,
            Product,
            Category,
            Unit,
            InventoryItem,
            active_reservations.c.reserved_quantity,
        )
        .join(Product, Product.id == ProductVariant.product_id)
        .outerjoin(
            Category,
            and_(Category.id == Product.category_id, Category.is_active.is_(True)),
        )
        .join(Unit, Unit.id == ProductVariant.unit_id)
        .outerjoin(InventoryItem, InventoryItem.variant_id == ProductVariant.id)
        .outerjoin(active_reservations, active_reservations.c.variant_id == ProductVariant.id)
        .where(
            ProductVariant.is_active.is_(True),
            Product.is_active.is_(True),
            Unit.is_active.is_(True),
        )
        .order_by(Product.name, ProductVariant.name, ProductVariant.id)
    ).all()

    return [
        StorefrontCatalogItem(
            variant_id=variant.id,
            variant_name=variant.name,
            sku=variant.sku,
            product_id=product.id,
            product_name=product.name,
            description=product.description,
            category_id=category.id if category else None,
            category_name=category.name if category else None,
            unit_id=unit.id,
            unit_name=unit.name,
            unit_symbol=unit.symbol,
            retail_price_rial=variant.retail_price_rial,
            available_quantity=max(Decimal("0"), (inventory.quantity_on_hand if inventory else Decimal("0")) - Decimal(reserved or 0)),
            image_url=product.image_url,
        )
        for variant, product, category, unit, inventory, reserved in rows
    ]
