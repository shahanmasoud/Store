from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.catalog import Category, Product, ProductVariant, Unit
from app.models.user import User


def seed_admin(db: Session) -> User:
    settings = get_settings()
    user = db.query(User).filter(User.username == settings.default_admin_username).first()
    if user:
        return user

    user = User(
        username=settings.default_admin_username,
        full_name=settings.default_admin_full_name,
        hashed_password=get_password_hash(settings.default_admin_password),
        is_active=True,
        is_superuser=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def seed_catalog(db: Session) -> None:
    kilo = db.query(Unit).filter(Unit.symbol == "kg").first()
    if not kilo:
        kilo = Unit(name="کیلوگرم", symbol="kg")
        db.add(kilo)
        db.flush()

    rice = db.query(Category).filter(Category.name == "برنج", Category.parent_id.is_(None)).first()
    if not rice:
        rice = Category(name="برنج")
        db.add(rice)
        db.flush()

    iranian_rice = db.query(Category).filter(Category.name == "ایرانی", Category.parent_id == rice.id).first()
    if not iranian_rice:
        iranian_rice = Category(name="ایرانی", parent_id=rice.id)
        db.add(iranian_rice)
        db.flush()

    product = db.query(Product).filter(Product.name == "برنج", Product.category_id == rice.id).first()
    if not product:
        product = Product(name="برنج", description="کالای پایه برای انواع برنج", category_id=rice.id)
        db.add(product)
        db.flush()

    variant = db.query(ProductVariant).filter(ProductVariant.name == "برنج ایرانی طارم").first()
    if not variant:
        db.add(
            ProductVariant(
                product_id=product.id,
                unit_id=kilo.id,
                name="برنج ایرانی طارم",
                sku="RICE-TAREM-IR",
                retail_price_rial=0,
            )
        )

    db.commit()


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        user = seed_admin(db)
        seed_catalog(db)
        print(f"Admin user is ready: {user.username}")


if __name__ == "__main__":
    main()

