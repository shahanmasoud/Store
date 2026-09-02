from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    retail_price_rial: int = 0
    wholesale_price_rial: int | None = None
    min_wholesale_quantity: Decimal | None = None

    @field_validator("name")
    @classmethod
    def normalize_variant_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("نام گونه نمی‌تواند خالی باشد.")
        return normalized

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @field_validator("retail_price_rial", "wholesale_price_rial", "min_wholesale_quantity")
    @classmethod
    def non_negative_variant_values(cls, value: int | Decimal | None) -> int | Decimal | None:
        if value is not None and value < 0:
            raise ValueError("قیمت و حداقل تعداد عمده نمی‌توانند منفی باشند.")
        return value


class ProductVariantUpdate(BaseModel):
    product_id: int | None = None
    unit_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=180)
    sku: str | None = Field(default=None, max_length=80)
    retail_price_rial: int | None = None
    wholesale_price_rial: int | None = None
    min_wholesale_quantity: Decimal | None = None

    @field_validator("product_id", "unit_id")
    @classmethod
    def required_reference_when_present(cls, value: int | None) -> int:
        if value is None:
            raise ValueError("کالا و واحد گونه باید مشخص باشند.")
        return value

    @field_validator("name")
    @classmethod
    def normalize_optional_variant_name(cls, value: str | None) -> str:
        if value is None or not value.strip():
            raise ValueError("نام گونه نمی‌تواند خالی باشد.")
        return value.strip()

    @field_validator("sku")
    @classmethod
    def normalize_optional_sku(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @field_validator("retail_price_rial", "wholesale_price_rial", "min_wholesale_quantity")
    @classmethod
    def non_negative_optional_variant_values(cls, value: int | Decimal | None) -> int | Decimal | None:
        if value is not None and value < 0:
            raise ValueError("قیمت و حداقل تعداد عمده نمی‌توانند منفی باشند.")
        return value


class ProductVariantRead(ProductVariantCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool


class PriceListCreate(BaseModel):
    variant_id: int
    price_type: str = Field(pattern="^(retail|wholesale|online)$")
    amount_rial: int
    jalali_date: str
    local_time: str

    @field_validator("amount_rial")
    @classmethod
    def non_negative_price(cls, value: int) -> int:
        if value < 0:
            raise ValueError("مبلغ قیمت نمی‌تواند منفی باشد.")
        return value

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
    min_quantity: Decimal
    discount_amount_rial: int | None = None
    discount_percent: Decimal | None = None
    starts_jalali_date: str | None = None

    @field_validator("min_quantity")
    @classmethod
    def non_negative_min_quantity(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("حداقل تعداد نمی‌تواند منفی باشد.")
        return value

    @field_validator("discount_amount_rial")
    @classmethod
    def non_negative_discount_amount(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("مبلغ تخفیف نمی‌تواند منفی باشد.")
        return value

    @field_validator("discount_percent")
    @classmethod
    def valid_discount_percent(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and (value < 0 or value > 100):
            raise ValueError("درصد تخفیف باید بین صفر تا صد باشد.")
        return value

    @field_validator("starts_jalali_date")
    @classmethod
    def optional_jalali_date_format(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return validate_jalali_date(value.strip())

    @model_validator(mode="after")
    def exactly_one_positive_discount(self) -> "PriceRuleCreate":
        has_amount = self.discount_amount_rial is not None and self.discount_amount_rial > 0
        has_percent = self.discount_percent is not None and self.discount_percent > 0
        if has_amount == has_percent:
            raise ValueError("دقیقاً یکی از مبلغ یا درصد تخفیف باید مقداری مثبت داشته باشد.")
        return self


class PriceRuleUpdate(BaseModel):
    variant_id: int | None = None
    min_quantity: Decimal | None = None
    discount_amount_rial: int | None = None
    discount_percent: Decimal | None = None
    starts_jalali_date: str | None = None

    @field_validator("variant_id", "min_quantity")
    @classmethod
    def required_value_when_present(cls, value: int | Decimal | None) -> int | Decimal:
        if value is None:
            raise ValueError("گونه و حداقل تعداد باید مشخص باشند.")
        if isinstance(value, Decimal) and value < 0:
            raise ValueError("حداقل تعداد نمی‌تواند منفی باشد.")
        return value

    @field_validator("discount_amount_rial")
    @classmethod
    def non_negative_optional_amount(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("مبلغ تخفیف نمی‌تواند منفی باشد.")
        return value

    @field_validator("discount_percent")
    @classmethod
    def valid_optional_percent(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and (value < 0 or value > 100):
            raise ValueError("درصد تخفیف باید بین صفر تا صد باشد.")
        return value

    @field_validator("starts_jalali_date")
    @classmethod
    def optional_update_jalali_date_format(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return validate_jalali_date(value.strip())


class PriceRuleRead(PriceRuleCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
