from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.numbers import normalize_identifier, normalize_localized_integer
from app.core.time import validate_jalali_date, validate_local_time

PersonType = Literal["customer", "supplier", "both"]
CreditStatus = Literal["good", "normal", "watch"]
LedgerEntryType = Literal["debit", "credit"]
LedgerSourceType = Literal["sale", "purchase", "settlement", "cheque", "manual"]
LedgerStatus = Literal["open", "settled", "canceled"]
ChequeType = Literal["received", "paid"]
ChequeStatus = Literal["pending", "cleared", "bounced", "canceled"]
ChequeEventType = Literal["created", "cleared", "bounced", "canceled"]
ChequeAuditAction = Literal["create", "update", "event", "legacy_snapshot"]


class PersonCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    phone: str | None = Field(default=None, max_length=40)
    person_type: PersonType
    note: str | None = Field(default=None, max_length=2000)
    credit_status: CreditStatus = "normal"

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, value):
        return normalize_identifier(value)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("نام شخص الزامی است.")
        return value

    @field_validator("phone", "note")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("person_type", mode="before")
    @classmethod
    def valid_person_type(cls, value: str) -> str:
        if value not in {"customer", "supplier", "both"}:
            raise ValueError("نوع شخص باید مشتری، تأمین‌کننده یا هر دو باشد.")
        return value

    @field_validator("credit_status", mode="before")
    @classmethod
    def valid_credit_status(cls, value: str) -> str:
        if value not in {"good", "normal", "watch"}:
            raise ValueError("وضعیت خوش‌حسابی باید خوب، عادی یا نیازمند بررسی باشد.")
        return value


class PersonUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    phone: str | None = Field(default=None, max_length=40)
    person_type: PersonType | None = None
    note: str | None = Field(default=None, max_length=2000)
    credit_status: CreditStatus | None = None

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, value):
        return normalize_identifier(value)

    @field_validator("name")
    @classmethod
    def update_name_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("نام شخص نمی‌تواند خالی باشد.")
        value = value.strip()
        if not value:
            raise ValueError("نام شخص نمی‌تواند خالی باشد.")
        return value

    @field_validator("phone", "note")
    @classmethod
    def update_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("person_type", mode="before")
    @classmethod
    def update_person_type(cls, value: str | None) -> str | None:
        if value is None or value not in {"customer", "supplier", "both"}:
            raise ValueError("نوع شخص باید مشتری، تأمین‌کننده یا هر دو باشد.")
        return value

    @field_validator("credit_status", mode="before")
    @classmethod
    def update_credit_status(cls, value: str | None) -> str | None:
        if value is None or value not in {"good", "normal", "watch"}:
            raise ValueError("وضعیت خوش‌حسابی باید خوب، عادی یا نیازمند بررسی باشد.")
        return value


class PersonRead(PersonCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool


class PersonAccountSummary(BaseModel):
    person_id: int
    debit_open_rial: int = Field(description="جمع مانده باز بدهی‌های فعال شخص")
    credit_open_rial: int = Field(description="جمع مانده باز بستانکاری‌های فعال شخص")
    net_balance_rial: int = Field(
        description="بدهی باز منهای بستانکاری باز؛ مثبت یعنی شخص به فروشگاه بدهکار و منفی یعنی فروشگاه به شخص بدهکار است"
    )
    open_entries_count: int


class LedgerEntryCreate(BaseModel):
    person_id: int
    entry_type: LedgerEntryType
    amount_rial: int = Field(gt=0)
    source_type: LedgerSourceType = "manual"
    source_id: int | None = None
    jalali_date: str
    due_jalali_date: str | None = None
    local_time: str
    description: str | None = None

    @field_validator("person_id", "amount_rial", "source_id", mode="before")
    @classmethod
    def localized_integers(cls, value):
        return normalize_localized_integer(value)

    @field_validator("jalali_date", "due_jalali_date")
    @classmethod
    def jalali_date_format(cls, value: str | None) -> str | None:
        if value is None:
            return None
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
    due_jalali_date: str | None
    local_time: str
    description: str | None
    status: LedgerStatus
    is_active: bool


class LedgerDueDateUpdate(BaseModel):
    due_jalali_date: str | None
    reason: str = Field(min_length=1, max_length=2000)

    @field_validator("due_jalali_date")
    @classmethod
    def due_date_format(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_jalali_date(value)

    @field_validator("reason")
    @classmethod
    def reason_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("دلیل تغییر سررسید الزامی است.")
        return value


class LedgerDueAuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entry_id: int
    actor_user_id: int | None
    actor_username: str | None
    actor_full_name: str | None
    before_due_date: str | None
    after_due_date: str | None
    reason: str
    occurred_at_utc: datetime


class ChequePersonOption(BaseModel):
    id: int
    name: str
    person_type: PersonType

    model_config = ConfigDict(from_attributes=True)


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

    @field_validator("person_id", "amount_rial", mode="before")
    @classmethod
    def localized_integers(cls, value):
        return normalize_localized_integer(value)

    @field_validator("cheque_number", mode="before")
    @classmethod
    def normalize_cheque_number(cls, value):
        return normalize_identifier(value)

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


class ChequeUpdate(BaseModel):
    person_id: int | None = None
    bank_name: str | None = Field(default=None, min_length=1, max_length=120)
    cheque_number: str | None = Field(default=None, min_length=1, max_length=80)
    amount_rial: int | None = Field(default=None, gt=0)
    issue_jalali_date: str | None = None
    due_jalali_date: str | None = None
    note: str | None = Field(default=None, max_length=2000)
    reason: str = Field(min_length=1, max_length=2000)
    expected_updated_at: datetime

    @field_validator("person_id", "amount_rial", mode="before")
    @classmethod
    def localized_integers(cls, value):
        return normalize_localized_integer(value)

    @field_validator("cheque_number", mode="before")
    @classmethod
    def normalize_cheque_number(cls, value):
        return normalize_identifier(value)

    @field_validator("bank_name", "cheque_number")
    @classmethod
    def required_text_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("این فیلد نمی‌تواند خالی باشد.")
        value = value.strip()
        if not value:
            raise ValueError("این فیلد نمی‌تواند خالی باشد.")
        return value

    @field_validator("issue_jalali_date", "due_jalali_date")
    @classmethod
    def jalali_date_format(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("تاریخ نمی‌تواند خالی باشد.")
        return validate_jalali_date(value)

    @field_validator("amount_rial")
    @classmethod
    def amount_not_null(cls, value: int | None) -> int:
        if value is None:
            raise ValueError("مبلغ نمی‌تواند خالی باشد.")
        return value

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @field_validator("reason")
    @classmethod
    def reason_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("دلیل ویرایش چک الزامی است.")
        return value


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
    created_at_utc: datetime
    updated_at_utc: datetime
    events: list[ChequeEventRead]


class ChequeAuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cheque_id: int
    action: ChequeAuditAction
    actor_user_id: int | None
    actor_username: str | None
    actor_full_name: str | None
    before_json: dict | None
    after_json: dict | None
    reason: str
    occurred_at_utc: datetime


class DuesRead(BaseModel):
    jalali_date_to: str
    open_ledger_entries: list[LedgerEntryRead]
    pending_cheques: list[ChequeRead]


DueReminderKind = Literal["ledger_entry", "cheque", "sale_payment"]
DueReminderDirection = Literal["receivable", "payable"]
DueReminderRecordType = Literal[
    "debit", "credit", "received", "paid", "cash", "card", "transfer", "cheque", "voucher"
]


class DueReminderItem(BaseModel):
    kind: DueReminderKind
    record_id: int
    payment_id: int | None = None
    invoice_id: int | None = None
    invoice_number: str | None = None
    person_id: int | None
    person_name: str | None
    customer_id: int | None = None
    customer_name: str | None = None
    direction: DueReminderDirection
    record_type: DueReminderRecordType
    amount_rial: int
    due_jalali_date: str
    status: str
    description: str | None
    cheque_number: str | None
    bank_name: str | None


class DueReminderTotals(BaseModel):
    count: int
    total_rial: int
    receivable_count: int
    receivable_total_rial: int
    payable_count: int
    payable_total_rial: int


class DueReminderGroup(DueReminderTotals):
    items: list[DueReminderItem]


class DueRemindersRead(BaseModel):
    today_jalali: str
    through_jalali: str
    overdue: DueReminderGroup
    today: DueReminderGroup
    upcoming: DueReminderGroup
    totals: DueReminderTotals
