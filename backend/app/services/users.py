from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.user import User


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def get_active_user_by_username(db: Session, username: str) -> User | None:
    user = get_user_by_username(db, username=username)
    if not user or not user.is_active:
        return None
    return user


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = get_active_user_by_username(db, username=username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def change_password(db: Session, *, user: User, new_password: str) -> None:
    user.hashed_password = get_password_hash(new_password)
    user.token_version += 1
    db.add(user)
    db.commit()

