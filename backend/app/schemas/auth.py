from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class UserRead(BaseModel):
    id: int
    username: str
    full_name: str
    is_active: bool
    is_superuser: bool
    can_sales: bool
    can_catalog_inventory: bool
    can_ledger: bool
    can_cheques_reports: bool
    created_at_utc: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def expose_effective_permissions(self) -> "UserRead":
        if self.is_superuser:
            self.can_sales = True
            self.can_catalog_inventory = True
            self.can_ledger = True
            self.can_cheques_reports = True
        return self


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def passwords_must_match_and_change(self) -> "ChangePasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("تکرار رمز عبور جدید با رمز جدید یکسان نیست.")
        if self.current_password == self.new_password:
            raise ValueError("رمز عبور جدید باید با رمز فعلی متفاوت باشد.")
        return self


class ChangePasswordResponse(BaseModel):
    message: str


class UserAdminCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=1, max_length=120)
    temporary_password: str = Field(min_length=8, max_length=128)
    can_sales: bool = False
    reason: str = Field(min_length=3, max_length=2000)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class UserAdminUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    can_sales: bool | None = None
    reason: str = Field(min_length=3, max_length=2000)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def require_change(self) -> "UserAdminUpdate":
        if self.full_name is None and self.can_sales is None:
            raise ValueError("حداقل یک تغییر برای کاربر مشخص کنید.")
        return self


class UserAdminDeactivate(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class UserAdminResetPassword(BaseModel):
    temporary_password: str = Field(min_length=8, max_length=128)
    reason: str = Field(min_length=3, max_length=2000)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

