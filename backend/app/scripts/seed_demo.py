from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.catalog import Category, Product, ProductVariant, Unit
from app.models.purchases import PurchaseInvoice
from app.models.sales import Payment
from app.schemas.purchases import PurchaseInvoiceCreate, PurchaseInvoiceItemCreate
from app.schemas.sales import PaymentCreate, SaleInvoiceCreate, SaleInvoiceItemCreate
from app.scripts.seed_admin import seed_admin, seed_catalog
from app.services.purchases import create_purchase
from app.services.sales import create_sale

DEMO_PURCHASE_NOTE = "PHASE09_DEMO_PURCHASE"
DEMO_SALE_REFERENCE = "PHASE09-DEMO-SALE"


def _get_or_create_unit(db: Session, *, name: str, symbol: str) -> Unit:
    unit = db.scalar(select(Unit).where(Unit.symbol == symbol))
    if unit:
        return unit
    unit = Unit(name=name, symbol=symbol)
    db.add(unit)
    db.flush()
    return unit


def _get_or_create_category(db: Session, *, name: str, parent: Category | None = None) -> Category:
    category = db.scalar(
        select(Category).where(
            Category.name == name,
            Category.parent_id == (parent.id if parent else None),
        )
    )
    if category:
        return category
    category = Category(name=name, parent_id=parent.id if parent else None)
    db.add(category)
    db.flush()
    return category


def _get_or_create_product(db: Session, *, name: str, category: Category, description: str) -> Product:
    product = db.scalar(select(Product).where(Product.name == name, Product.category_id == category.id))
    if product:
        return product
    product = Product(name=name, category_id=category.id, description=description)
    db.add(product)
    db.flush()
    return product


def _get_or_create_variant(
    db: Session,
    *,
    product: Product,
    unit: Unit,
    name: str,
    sku: str,
    retail_price_rial: int,
    wholesale_price_rial: int,
    min_wholesale_quantity: Decimal,
) -> ProductVariant:
    variant = db.scalar(select(ProductVariant).where(ProductVariant.sku == sku))
    if variant:
        return variant
    variant = ProductVariant(
        product_id=product.id,
        unit_id=unit.id,
        name=name,
        sku=sku,
        retail_price_rial=retail_price_rial,
        wholesale_price_rial=wholesale_price_rial,
        min_wholesale_quantity=min_wholesale_quantity,
    )
    db.add(variant)
    db.flush()
    return variant


def _ensure_demo_catalog(db: Session) -> list[ProductVariant]:
    kilo = _get_or_create_unit(db, name="کیلوگرم", symbol="kg")
    legumes = _get_or_create_category(db, name="حبوبات")

    beans = _get_or_create_product(
        db,
        name="لوبیا",
        category=legumes,
        description="داده نمایشی برای تست فروشگاه حبوبات",
    )
    lentils = _get_or_create_product(
        db,
        name="عدس",
        category=legumes,
        description="داده نمایشی برای تست موجودی و فروش",
    )
    chickpeas = _get_or_create_product(
        db,
        name="نخود",
        category=legumes,
        description="داده نمایشی برای تست خرید و گزارش‌ها",
    )

    variants = [
        _get_or_create_variant(
            db,
            product=beans,
            unit=kilo,
            name="لوبیا چیتی ممتاز",
            sku="DEMO-BEAN-PINTO",
            retail_price_rial=1_850_000,
            wholesale_price_rial=1_720_000,
            min_wholesale_quantity=Decimal("20"),
        ),
        _get_or_create_variant(
            db,
            product=lentils,
            unit=kilo,
            name="عدس ریز ایرانی",
            sku="DEMO-LENTIL-IR",
            retail_price_rial=1_240_000,
            wholesale_price_rial=1_150_000,
            min_wholesale_quantity=Decimal("25"),
        ),
        _get_or_create_variant(
            db,
            product=chickpeas,
            unit=kilo,
            name="نخود کرمانشاه",
            sku="DEMO-CHICKPEA-KSH",
            retail_price_rial=1_480_000,
            wholesale_price_rial=1_360_000,
            min_wholesale_quantity=Decimal("20"),
        ),
    ]
    db.commit()
    return variants


def _ensure_demo_purchase(db: Session, variants: list[ProductVariant]) -> bool:
    existing = db.scalar(select(PurchaseInvoice).where(PurchaseInvoice.note == DEMO_PURCHASE_NOTE))
    if existing:
        return False

    create_purchase(
        db,
        PurchaseInvoiceCreate(
            supplier_name="تامین‌کننده نمونه حبوبات",
            jalali_date="1405/06/01",
            local_time="09:15",
            paid_total_rial=120_000_000,
            note=DEMO_PURCHASE_NOTE,
            items=[
                PurchaseInvoiceItemCreate(variant_id=variants[0].id, quantity=Decimal("80"), unit_cost_rial=1_320_000),
                PurchaseInvoiceItemCreate(variant_id=variants[1].id, quantity=Decimal("120"), unit_cost_rial=880_000),
                PurchaseInvoiceItemCreate(variant_id=variants[2].id, quantity=Decimal("95"), unit_cost_rial=1_020_000),
            ],
        ),
    )
    return True


def _ensure_demo_sale(db: Session, variants: list[ProductVariant]) -> bool:
    existing = db.scalar(select(Payment).where(Payment.reference_number == DEMO_SALE_REFERENCE))
    if existing:
        return False

    create_sale(
        db,
        SaleInvoiceCreate(
            customer_name="مشتری نمونه فروشگاه",
            jalali_date="1405/06/02",
            local_time="11:40",
            discount_amount_rial=250_000,
            note="فروش نمایشی فاز ۰۹ برای تست دفتر روزانه",
            items=[
                SaleInvoiceItemCreate(
                    variant_id=variants[0].id,
                    quantity=Decimal("4"),
                    unit_price_rial=1_850_000,
                    discount_amount_rial=100_000,
                    estimated_cost_rial=5_280_000,
                ),
                SaleInvoiceItemCreate(
                    variant_id=variants[1].id,
                    quantity=Decimal("6"),
                    unit_price_rial=1_240_000,
                    discount_amount_rial=0,
                    estimated_cost_rial=5_280_000,
                ),
            ],
            payments=[
                PaymentCreate(
                    method="card",
                    amount_rial=8_000_000,
                    reference_number=DEMO_SALE_REFERENCE,
                ),
                PaymentCreate(
                    method="credit",
                    amount_rial=6_490_000,
                    due_jalali_date="1405/06/10",
                    note="مانده نمایشی برای تست گزارش بدهی",
                ),
            ],
        ),
    )
    return True


def seed_demo(db: Session) -> dict[str, int | bool | str]:
    user = seed_admin(db)
    seed_catalog(db)
    variants = _ensure_demo_catalog(db)
    created_purchase = _ensure_demo_purchase(db, variants)
    created_sale = _ensure_demo_sale(db, variants)
    return {
        "admin_username": user.username,
        "demo_variants": len(variants),
        "created_purchase": created_purchase,
        "created_sale": created_sale,
    }


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        result = seed_demo(db)
        print(
            "Demo seed ready: "
            f"admin={result['admin_username']}, "
            f"variants={result['demo_variants']}, "
            f"created_purchase={result['created_purchase']}, "
            f"created_sale={result['created_sale']}"
        )


if __name__ == "__main__":
    main()
