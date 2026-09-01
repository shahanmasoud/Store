from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.time import validate_jalali_date, validate_local_time


class UnitCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    symbol: str = Field(min_length=1, max_length=20)

    @field_validator("name", "symbol")
    @classmethod
    def normalize_unit_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("نام و نماد واحد نمی‌توانند خالی باشند.")
        return normalized


class UnitUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    symbol: str | None = Field(default=None, min_length=1, max_length=20)

    @field_validator("name", "symbol")
    @classmethod
    def normalize_optional_unit_text(cls, value: str | None) -> str:
        if value is None or not value.strip():
            raise ValueError("نام و نماد واحد نمی‌توانند خالی باشند.")
        return value.strip()


class UnitRead(UnitCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    parent_id: int | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("نام دسته نمی‌تواند خالی باشد.")
        return normalized


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    parent_id: int | None = None

    @field_validator("name")
    @classmethod
    def normalize_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("نام دسته نمی‌تواند خالی باشد.")
        normalized = value.strip()
        if not normalized:
            raise ValueError("نام دسته نمی‌تواند خالی باشد.")
        return normalized


class CategoryRead(CategoryCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    category_id: int | None = None

    @field_validator("name")
    @classmethod
    def normalize_product_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("نام کالا نمی‌تواند خالی باشد.")
        return normalized


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    category_id: int | None = None

    @field_validator("name")
    @classmethod
    def normalize_optional_product_name(cls, value: str | None) -> str:
        if value is None or not value.strip():
            raise ValueError("نام کالا نمی‌تواند خالی باشد.")
        return value.strip()


class ProductRead(ProductCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool


class ProductVariantCreate(BaseModel):
    product_id: int
    unit_id: int
    name: str = Field(min_length=1, max_length=180)
    sku: str | None = Field(default=None, max_length=80)
    retail_price_rial: int = Field(default=0, ge=0)
    wholesale_price_rial: int | None = Field(default=None, ge=0)
    min_wholesale_quantity: Decimal | None = Field(default=None, ge=0)


class ProductVariantRead(ProductVariantCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool


class PriceListCreate(BaseModel):
    variant_id: int
    price_type: str = Field(pattern="^(retail|wholesale|online)$")
    amount_rial: int = Field(ge=0)
    jalali_date: str
    local_time: str

    @field_validator("jalali_date")
    @classmethod
    def jalali_date_format(cls, value: str) -> str:
        return validate_jalali_date(value)

    @field_validator("local_time")
    @classmethod
    def local_time_format(cls, value: str) -> str:
        return validate_local_time(value)


class PriceListRead(PriceListCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timezone: str
    is_active: bool


class PriceRuleCreate(BaseModel):
    variant_id: int
    min_quantity: Decimal = Field(ge=0)
    discount_amount_rial: int | None = Field(default=None, ge=0)
    discount_percent: Decimal | None = Field(default=None, ge=0, le=100)
    starts_jalali_date: str | None = None

    @field_validator("starts_jalali_date")
    @classmethod
    def optional_jalali_date_format(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_jalali_date(value)


class PriceRuleRead(PriceRuleCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
