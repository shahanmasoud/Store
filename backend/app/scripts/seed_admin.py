from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import SessionLocal, engine
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


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        user = seed_admin(db)
        print(f"Admin user is ready: {user.username}")


if __name__ == "__main__":
    main()

