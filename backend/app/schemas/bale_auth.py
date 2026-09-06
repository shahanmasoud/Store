from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


BaleChallengeStatus = Literal["pending", "approved", "consumed", "expired"]


class BaleChallengeCreate(BaseModel):
    return_path: str = Field(default="/", min_length=1, max_length=255)

    @field_validator("return_path")
    @classmethod
    def validate_internal_return_path(cls, value: str) -> str:
        if not value.startswith("/") or value.startswith("//") or "://" in value:
            raise ValueError("مسیر بازگشت باید داخل همین سایت باشد.")
        return value


class BaleChallengeCreated(BaseModel):
    id: str
    code: str
    status: BaleChallengeStatus
    expires_at_utc: datetime
    expires_in_seconds: int
    bot_url: str
    poll_after_seconds: int = 2


class BaleChallengeRead(BaseModel):
    id: str
    status: BaleChallengeStatus
    expires_at_utc: datetime
    expires_in_seconds: int
    poll_after_seconds: int = 2


class CustomerRead(BaseModel):
    id: int
    display_name: str | None = None
    provider: Literal["bale"] = "bale"


class BaleChallengeExchange(BaseModel):
    access_token: str
    token_type: str = "bearer"
    return_path: str
    customer: CustomerRead
