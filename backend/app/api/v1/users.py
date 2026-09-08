from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.v1.auth import require_superuser
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    UserAdminCreate,
    UserAdminDeactivate,
    UserAdminResetPassword,
    UserAdminUpdate,
    UserRead,
)
from app.services import users as user_service

router = APIRouter(dependencies=[Depends(require_superuser)])


@router.get("/users", response_model=list[UserRead])
def users(db: Session = Depends(get_db)) -> list[User]:
    return user_service.list_users(db)


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserAdminCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_superuser),
) -> User:
    return user_service.create_subadmin(db, payload, actor=actor)


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserAdminUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_superuser),
) -> User:
    return user_service.update_subadmin(db, user_id, payload, actor=actor)


@router.post("/users/{user_id}/deactivate", response_model=UserRead)
def deactivate_user(
    user_id: int,
    payload: UserAdminDeactivate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_superuser),
) -> User:
    return user_service.deactivate_subadmin(db, user_id, payload.reason, actor=actor)


@router.post("/users/{user_id}/reset-password", response_model=UserRead)
def reset_user_password(
    user_id: int,
    payload: UserAdminResetPassword,
    db: Session = Depends(get_db),
    actor: User = Depends(require_superuser),
) -> User:
    return user_service.reset_subadmin_password(
        db,
        user_id,
        payload.temporary_password,
        payload.reason,
        actor=actor,
    )
