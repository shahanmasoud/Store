from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.core.security import get_password_hash, verify_password
from app.models.user import User, UserAdminAudit
from app.schemas.auth import UserAdminCreate, UserAdminUpdate


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


def _snapshot(user: User) -> dict[str, object]:
    """Return an audit-safe user snapshot. Password hashes and token versions are intentionally excluded."""
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "can_sales": user.can_sales,
        "can_catalog_inventory": user.can_catalog_inventory,
        "can_ledger": user.can_ledger,
        "can_cheques_reports": user.can_cheques_reports,
    }


def _audit(
    db: Session,
    *,
    actor: User,
    target: User,
    action: str,
    before: dict[str, object] | None,
    after: dict[str, object] | None,
    reason: str,
) -> None:
    db.add(
        UserAdminAudit(
            actor_user_id=actor.id,
            target_user_id=target.id,
            action=action,
            before_json=before,
            after_json=after,
            reason=reason,
            occurred_at_utc=utc_now(),
        )
    )


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.is_active.desc(), User.id)))


def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="کاربر پیدا نشد.")
    return user


def _ensure_subadmin_target(target: User) -> None:
    if target.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="حساب مدیر اصلی از مسیر مدیریت زیرمدیر قابل تغییر نیست.",
        )


def create_subadmin(db: Session, payload: UserAdminCreate, *, actor: User) -> User:
    username = payload.username.lower()
    if get_user_by_username(db, username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="این نام کاربری قبلاً ثبت شده است.")
    user = User(
        username=username,
        full_name=payload.full_name,
        hashed_password=get_password_hash(payload.temporary_password),
        is_active=True,
        is_superuser=False,
        can_sales=payload.can_sales,
        can_catalog_inventory=payload.can_catalog_inventory,
        can_ledger=payload.can_ledger,
        can_cheques_reports=payload.can_cheques_reports,
    )
    db.add(user)
    db.flush()
    _audit(
        db,
        actor=actor,
        target=user,
        action="create",
        before=None,
        after=_snapshot(user),
        reason=payload.reason,
    )
    db.commit()
    db.refresh(user)
    return user


def update_subadmin(db: Session, user_id: int, payload: UserAdminUpdate, *, actor: User) -> User:
    target = get_user_or_404(db, user_id)
    _ensure_subadmin_target(target)
    before = _snapshot(target)
    permission_changed = (
        (payload.can_sales is not None and payload.can_sales != target.can_sales)
        or (
            payload.can_catalog_inventory is not None
            and payload.can_catalog_inventory != target.can_catalog_inventory
        )
        or (payload.can_ledger is not None and payload.can_ledger != target.can_ledger)
        or (payload.can_cheques_reports is not None and payload.can_cheques_reports != target.can_cheques_reports)
    )
    if payload.full_name is not None:
        target.full_name = payload.full_name
    if payload.can_sales is not None:
        target.can_sales = payload.can_sales
    if payload.can_catalog_inventory is not None:
        target.can_catalog_inventory = payload.can_catalog_inventory
    if payload.can_ledger is not None:
        target.can_ledger = payload.can_ledger
    if payload.can_cheques_reports is not None:
        target.can_cheques_reports = payload.can_cheques_reports
    if permission_changed:
        target.token_version += 1
    db.add(target)
    _audit(
        db,
        actor=actor,
        target=target,
        action="update",
        before=before,
        after=_snapshot(target),
        reason=payload.reason,
    )
    db.commit()
    db.refresh(target)
    return target


def deactivate_subadmin(db: Session, user_id: int, reason: str, *, actor: User) -> User:
    target = get_user_or_404(db, user_id)
    if target.id == actor.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="نمی‌توانید حساب خودتان را غیرفعال کنید.")
    _ensure_subadmin_target(target)
    if not target.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="این کاربر قبلاً غیرفعال شده است.")
    before = _snapshot(target)
    target.is_active = False
    target.token_version += 1
    db.add(target)
    _audit(
        db,
        actor=actor,
        target=target,
        action="deactivate",
        before=before,
        after=_snapshot(target),
        reason=reason,
    )
    db.commit()
    db.refresh(target)
    return target


def reset_subadmin_password(db: Session, user_id: int, password: str, reason: str, *, actor: User) -> User:
    target = get_user_or_404(db, user_id)
    if target.id == actor.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="برای تغییر رمز خودتان از گزینه تغییر رمز عبور استفاده کنید.",
        )
    _ensure_subadmin_target(target)
    if not target.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="رمز کاربر غیرفعال قابل بازنشانی نیست.")
    before = _snapshot(target)
    target.hashed_password = get_password_hash(password)
    target.token_version += 1
    db.add(target)
    _audit(
        db,
        actor=actor,
        target=target,
        action="reset_password",
        before=before,
        after=_snapshot(target),
        reason=reason,
    )
    db.commit()
    db.refresh(target)
    return target

