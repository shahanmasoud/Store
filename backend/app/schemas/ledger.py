from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.time import validate_jalali_date, validate_local_time

PersonType = Literal["customer", "supplier", "both"]
LedgerEntryType = Literal["debit", "credit"]
LedgerSourceType = Literal["sale", "purchase", "settlement", "cheque", "manual"]
LedgerStatus = Literal["open", "settled", "canceled"]
ChequeType = Literal["received", "paid"]
ChequeStatus = Literal["pending", "cleared", "bounced", "canceled"]
ChequeEventType = Literal["created", "cleared", "bounced", "canceled"]


class PersonCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    phone: str | None = Field(default=None, max_length=40)
    person_type: PersonType

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("نام شخص الزامی است.")
        return value


class PersonRead(PersonCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool


class LedgerEntryCreate(BaseModel):
    person_id: int
    entry_type: LedgerEntryType
    amount_rial: int = Field(gt=0)
    source_type: LedgerSourceType = "manual"
    source_id: int | None = None
    jalali_date: str
    local_time: str
    description: str | None = None

    @field_validator("jalali_date")
    @classmethod
    def jalali_date_format(cls, value: str) -> str:
        return validate_jalali_date(value)

    @field_validator("local_time")
    @classmethod
    def local_time_format(cls, value: str) -> str:
        return validate_local_time(value)


class LedgerEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    person_id: int
    entry_type: LedgerEntryType
    amount_rial: int
    remaining_rial: int
    source_type: LedgerSourceType
    source_id: int | None
    jalali_date: str
    local_time: str
    description: str | None
    status: LedgerStatus
    is_active: bool


class SettlementCreate(BaseModel):
    person_id: int
    entry_type: LedgerEntryType = "debit"
    amount_rial: int = Field(gt=0)
    jalali_date: str
    local_time: str
    note: str | None = None

    @field_validator("jalali_date")
    @classmethod
    def jalali_date_format(cls, value: str) -> str:
        return validate_jalali_date(value)

    @field_validator("local_time")
    @classmethod
    def local_time_format(cls, value: str) -> str:
        return validate_local_time(value)


class SettlementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    person_id: int
    entry_type: LedgerEntryType
    amount_rial: int
    jalali_date: str
    local_time: str
    note: str | None


class ChequeCreate(BaseModel):
    cheque_type: ChequeType
    person_id: int | None = None
    bank_name: str = Field(min_length=1, max_length=120)
    cheque_number: str = Field(min_length=1, max_length=80)
    amount_rial: int = Field(gt=0)
    issue_jalali_date: str
    due_jalali_date: str
    local_time: str
    note: str | None = None

    @field_validator("bank_name", "cheque_number")
    @classmethod
    def required_text_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("این فیلد الزامی است.")
        return value

    @field_validator("issue_jalali_date", "due_jalali_date")
    @classmethod
    def jalali_date_format(cls, value: str) -> str:
        return validate_jalali_date(value)

    @field_validator("local_time")
    @classmethod
    def local_time_format(cls, value: str) -> str:
        return validate_local_time(value)

    @model_validator(mode="after")
    def due_date_not_before_issue_date(self) -> "ChequeCreate":
        if self.due_jalali_date < self.issue_jalali_date:
            raise ValueError("تاریخ سررسید نمی‌تواند پیش از تاریخ صدور باشد.")
        return self


class ChequeEventCreate(BaseModel):
    event_type: Literal["cleared", "bounced", "canceled"]
    jalali_date: str
    local_time: str
    note: str | None = None

    @field_validator("jalali_date")
    @classmethod
    def jalali_date_format(cls, value: str) -> str:
        return validate_jalali_date(value)

    @field_validator("local_time")
    @classmethod
    def local_time_format(cls, value: str) -> str:
        return validate_local_time(value)


class ChequeEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cheque_id: int
    event_type: ChequeEventType
    jalali_date: str
    local_time: str
    note: str | None


class ChequeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cheque_type: ChequeType
    person_id: int | None
    bank_name: str
    cheque_number: str
    amount_rial: int
    issue_jalali_date: str
    due_jalali_date: str
    status: ChequeStatus
    note: str | None
    is_active: bool
    events: list[ChequeEventRead]


class DuesRead(BaseModel):
    jalali_date_to: str
    open_ledger_entries: list[LedgerEntryRead]
    pending_cheques: list[ChequeRead]
