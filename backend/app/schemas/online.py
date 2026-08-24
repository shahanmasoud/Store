from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.time import validate_jalali_date, validate_local_time


class OnlineChannelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    token: str = Field(min_length=16, max_length=160)
    note: str | None = None


class OnlineChannelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    note: str | None
    is_active: bool


class OnlinePriceRuleCreate(BaseModel):
    channel_id: int
    variant_id: int
    price_rial: int = Field(ge=0)
    min_quantity: Decimal = Field(default=Decimal("1"), gt=0)
    starts_jalali_date: str | None = None
    ends_jalali_date: str | None = None

    @field_validator("starts_jalali_date", "ends_jalali_date")
    @classmethod
    def optional_jalali_date_format(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_jalali_date(value)


class OnlinePriceRuleRead(OnlinePriceRuleCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool


class StockReservationCreate(BaseModel):
    channel_id: int
    variant_id: int
    quantity: Decimal = Field(gt=0)
    expires_jalali_date: str | None = None
    local_time: str
    note: str | None = None

    @field_validator("expires_jalali_date")
    @classmethod
    def optional_jalali_date_format(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_jalali_date(value)

    @field_validator("local_time")
    @classmethod
    def local_time_format(cls, value: str) -> str:
        return validate_local_time(value)


class StockReservationRead(StockReservationCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int | None
    status: str
    timezone: str
    is_active: bool


class OnlineCatalogItemRead(BaseModel):
    variant_id: int
    name: str
    sku: str | None
    retail_price_rial: int
    online_price_rial: int
    available_quantity: Decimal


class OnlineOrderItemCreate(BaseModel):
    variant_id: int
    quantity: Decimal = Field(gt=0)


class OnlineOrderCreate(BaseModel):
    external_order_id: str = Field(min_length=1, max_length=120)
    customer_name: str | None = Field(default=None, max_length=160)
    customer_phone: str | None = Field(default=None, max_length=40)
    discount_amount_rial: int = Field(default=0, ge=0)
    jalali_date: str
    local_time: str
    note: str | None = None
    items: list[OnlineOrderItemCreate] = Field(min_length=1)

    @field_validator("jalali_date")
    @classmethod
    def jalali_date_format(cls, value: str) -> str:
        return validate_jalali_date(value)

    @field_validator("local_time")
    @classmethod
    def local_time_format(cls, value: str) -> str:
        return validate_local_time(value)


class OnlineOrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    variant_id: int
    quantity: Decimal
    unit_price_rial: int
    line_total_rial: int
    product_snapshot: str


class OnlineOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    channel_id: int
    external_order_id: str
    customer_name: str | None
    customer_phone: str | None
    subtotal_rial: int
    discount_amount_rial: int
    total_rial: int
    status: str
    jalali_date: str
    local_time: str
    timezone: str
    is_active: bool
    items: list[OnlineOrderItemRead]
