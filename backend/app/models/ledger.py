from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.catalog import TimestampMixin


class Person(Base, TimestampMixin):
    __tablename__ = "persons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(40))
    person_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    ledger_entries: Mapped[list["LedgerEntry"]] = relationship(back_populates="person")
    settlements: Mapped[list["Settlement"]] = relationship(back_populates="person")
    cheques: Mapped[list["Cheque"]] = relationship(back_populates="person")


class LedgerEntry(Base, TimestampMixin):
    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), nullable=False, index=True)
    entry_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    amount_rial: Mapped[int] = mapped_column(Integer, nullable=False)
    remaining_rial: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    source_id: Mapped[int | None] = mapped_column(Integer)
    jalali_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    local_time: Mapped[str] = mapped_column(String(5), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    person: Mapped[Person] = relationship(back_populates="ledger_entries")


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
    events: Mapped[list["ChequeEvent"]] = relationship(back_populates="cheque", cascade="all, delete-orphan")


class ChequeEvent(Base, TimestampMixin):
    __tablename__ = "cheque_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cheque_id: Mapped[int] = mapped_column(ForeignKey("cheques.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    jalali_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    local_time: Mapped[str] = mapped_column(String(5), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)

    cheque: Mapped[Cheque] = relationship(back_populates="events")
