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
    created_at_utc: datetime

    model_config = ConfigDict(from_attributes=True)


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

