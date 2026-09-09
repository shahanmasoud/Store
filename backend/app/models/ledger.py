from datetime import datetime

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.core.time import utc_now
from app.models.catalog import TimestampMixin


class Person(Base, TimestampMixin):
    __tablename__ = "persons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(40))
    person_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(Text)
    credit_status: Mapped[str] = mapped_column(String(20), default="normal", nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    ledger_entries: Mapped[list["LedgerEntry"]] = relationship(back_populates="person")
    settlements: Mapped[list["Settlement"]] = relationship(back_populates="person")
    cheques: Mapped[list["Cheque"]] = relationship(back_populates="person")


class LedgerEntry(Base, TimestampMixin):
    __tablename__ = "ledger_entries"
    __table_args__ = (
        Index(
            "uq_ledger_entries_sale_source",
            "source_type",
            "source_id",
            unique=True,
            sqlite_where=text("source_type = 'sale' AND source_id IS NOT NULL"),
            postgresql_where=text("source_type = 'sale' AND source_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), nullable=False, index=True)
    entry_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    amount_rial: Mapped[int] = mapped_column(Integer, nullable=False)
    remaining_rial: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    source_id: Mapped[int | None] = mapped_column(Integer)
    jalali_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    due_jalali_date: Mapped[str | None] = mapped_column(String(10), index=True)
    local_time: Mapped[str] = mapped_column(String(5), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    person: Mapped[Person] = relationship(back_populates="ledger_entries")
    due_audits: Mapped[list["LedgerDueAudit"]] = relationship(
        back_populates="entry",
        cascade="all, delete-orphan",
        order_by="LedgerDueAudit.id",
    )
    settlement_allocations: Mapped[list["SettlementAllocation"]] = relationship(
        back_populates="ledger_entry",
        order_by="SettlementAllocation.id",
    )


class LedgerDueAudit(Base):
    __tablename__ = "ledger_due_audits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("ledger_entries.id"), nullable=False, index=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    actor_username: Mapped[str | None] = mapped_column(String(50))
    actor_full_name: Mapped[str | None] = mapped_column(String(120))
    before_due_date: Mapped[str | None] = mapped_column(String(10))
    after_due_date: Mapped[str | None] = mapped_column(String(10))
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    entry: Mapped[LedgerEntry] = relationship(back_populates="due_audits")


class LedgerActionAudit(Base):
    __tablename__ = "ledger_action_audits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    actor_username: Mapped[str | None] = mapped_column(String(50))
    actor_full_name: Mapped[str | None] = mapped_column(String(120))
    before_json: Mapped[dict | None] = mapped_column(JSON)
    after_json: Mapped[dict | None] = mapped_column(JSON)
    reason: Mapped[str | None] = mapped_column(Text)
    occurred_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class Settlement(Base, TimestampMixin):
    __tablename__ = "settlements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), nullable=False, index=True)
    entry_type: Mapped[str] = mapped_column(String(20), default="debit", nullable=False, index=True)
    amount_rial: Mapped[int] = mapped_column(Integer, nullable=False)
    jalali_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    local_time: Mapped[str] = mapped_column(String(5), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)

    person: Mapped[Person] = relationship(back_populates="settlements")
    allocations: Mapped[list["SettlementAllocation"]] = relationship(
        back_populates="settlement",
        order_by="SettlementAllocation.id",
    )


class SettlementAllocation(Base):
    """Append-only evidence of how a settlement consumed ledger entries."""

    __tablename__ = "settlement_allocations"
    __table_args__ = (CheckConstraint("amount_rial > 0", name="ck_settlement_allocations_amount_positive"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    settlement_id: Mapped[int] = mapped_column(ForeignKey("settlements.id"), nullable=False, index=True)
    ledger_entry_id: Mapped[int] = mapped_column(ForeignKey("ledger_entries.id"), nullable=False, index=True)
    amount_rial: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    settlement: Mapped[Settlement] = relationship(back_populates="allocations")
    ledger_entry: Mapped[LedgerEntry] = relationship(back_populates="settlement_allocations")


class Cheque(Base, TimestampMixin):
    __tablename__ = "cheques"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cheque_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    person_id: Mapped[int | None] = mapped_column(ForeignKey("persons.id"), index=True)
    bank_name: Mapped[str] = mapped_column(String(120), nullable=False)
    cheque_number: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    amount_rial: Mapped[int] = mapped_column(Integer, nullable=False)
    issue_jalali_date: Mapped[str] = mapped_column(String(10), nullable=False)
    due_jalali_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    person: Mapped[Person | None] = relationship(back_populates="cheques")
    events: Mapped[list["ChequeEvent"]] = relationship(
        back_populates="cheque",
        cascade="all, delete-orphan",
        order_by=lambda: (ChequeEvent.jalali_date, ChequeEvent.local_time, ChequeEvent.id),
    )
    audits: Mapped[list["ChequeAudit"]] = relationship(
        back_populates="cheque",
        order_by=lambda: (ChequeAudit.occurred_at_utc, ChequeAudit.id),
    )


class ChequeEvent(Base, TimestampMixin):
    __tablename__ = "cheque_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cheque_id: Mapped[int] = mapped_column(ForeignKey("cheques.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    jalali_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    local_time: Mapped[str] = mapped_column(String(5), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)

    cheque: Mapped[Cheque] = relationship(back_populates="events")


class ChequeAudit(Base):
    __tablename__ = "cheque_audits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cheque_id: Mapped[int] = mapped_column(ForeignKey("cheques.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    actor_username: Mapped[str | None] = mapped_column(String(50))
    actor_full_name: Mapped[str | None] = mapped_column(String(120))
    before_json: Mapped[dict | None] = mapped_column(JSON)
    after_json: Mapped[dict | None] = mapped_column(JSON)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    cheque: Mapped[Cheque] = relationship(back_populates="audits")
