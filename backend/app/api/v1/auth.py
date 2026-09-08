from collections.abc import Callable
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, decode_access_token, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, ChangePasswordResponse, LoginRequest, LoginResponse, UserRead
from app.services.users import authenticate_user, change_password, get_active_user_by_username

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="نشست شما معتبر نیست. لطفا دوباره وارد شوید.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        username = payload.get("sub")
        if not username:
            raise credentials_error
    except JWTError as exc:
        raise credentials_error from exc

    user = get_active_user_by_username(db, username=username)
    if not user:
        raise credentials_error
    if payload.get("ver", 0) != user.token_version:
        raise credentials_error
    return user


def require_superuser(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="فقط مدیر اصلی اجازه انجام این عملیات را دارد.",
        )
    return current_user


PermissionName = Literal["can_sales", "can_catalog_inventory", "can_ledger", "can_cheques_reports"]


def require_permission(permission: PermissionName) -> Callable[..., User]:
    def permission_dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.is_superuser or bool(getattr(current_user, permission, False)):
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="شما اجازه دسترسی به این بخش را ندارید.",
        )

    return permission_dependency


def require_any_permission(*permissions: PermissionName) -> Callable[..., User]:
    def permission_dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.is_superuser or any(bool(getattr(current_user, permission, False)) for permission in permissions):
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="شما اجازه دسترسی به این بخش را ندارید.",
        )

    return permission_dependency


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = authenticate_user(db, username=payload.username, password=payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="نام کاربری یا رمز عبور اشتباه است.",
        )

    token = create_access_token(subject=user.username, token_version=user.token_version)
    return LoginResponse(access_token=token, user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/change-password", response_model=ChangePasswordResponse)
def update_current_user_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChangePasswordResponse:
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="رمز عبور فعلی درست نیست.")
    change_password(db, user=current_user, new_password=payload.new_password)
    return ChangePasswordResponse(message="رمز عبور با موفقیت تغییر کرد. لطفاً دوباره وارد شوید.")
