from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.ledger import Cheque, ChequeEvent, LedgerEntry, Person, Settlement
from app.schemas.ledger import (
    ChequeCreate,
    ChequeEventCreate,
    DuesRead,
    LedgerEntryCreate,
    PersonCreate,
    SettlementCreate,
)


def _person_or_404(db: Session, person_id: int) -> Person:
    person = db.get(Person, person_id)
    if not person or not person.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found.")
    return person


def _cheque_or_404(db: Session, cheque_id: int) -> Cheque:
    cheque = db.scalar(
        select(Cheque)
        .options(selectinload(Cheque.events))
        .where(Cheque.id == cheque_id)
    )
    if not cheque:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cheque not found.")
    return cheque


def create_person(db: Session, payload: PersonCreate) -> Person:
    person = Person(name=payload.name, phone=payload.phone, person_type=payload.person_type)
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


def list_persons(db: Session) -> list[Person]:
    return list(db.scalars(select(Person).where(Person.is_active.is_(True)).order_by(Person.name, Person.id)))


def create_manual_entry(db: Session, payload: LedgerEntryCreate) -> LedgerEntry:
    _person_or_404(db, payload.person_id)
    entry = LedgerEntry(
        person_id=payload.person_id,
        entry_type=payload.entry_type,
        amount_rial=payload.amount_rial,
        remaining_rial=payload.amount_rial,
        source_type=payload.source_type,
        source_id=payload.source_id,
        jalali_date=payload.jalali_date,
        local_time=payload.local_time,
        description=payload.description,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_person_ledger(db: Session, person_id: int) -> list[LedgerEntry]:
    _person_or_404(db, person_id)
    return list(
        db.scalars(
            select(LedgerEntry)
            .where(LedgerEntry.person_id == person_id, LedgerEntry.is_active.is_(True))
            .order_by(LedgerEntry.jalali_date, LedgerEntry.local_time, LedgerEntry.id)
        )
    )


def create_settlement(db: Session, payload: SettlementCreate) -> Settlement:
    _person_or_404(db, payload.person_id)
    open_entries = list(
        db.scalars(
            select(LedgerEntry)
            .where(
                LedgerEntry.person_id == payload.person_id,
                LedgerEntry.status == "open",
                LedgerEntry.remaining_rial > 0,
                LedgerEntry.is_active.is_(True),
            )
            .order_by(LedgerEntry.jalali_date, LedgerEntry.local_time, LedgerEntry.id)
        )
    )
    open_balance = sum(entry.remaining_rial for entry in open_entries)
    if payload.amount_rial > open_balance:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Settlement exceeds open balance.")

    remaining_settlement = payload.amount_rial
    for entry in open_entries:
        if remaining_settlement <= 0:
            break
        applied = min(entry.remaining_rial, remaining_settlement)
        entry.remaining_rial -= applied
        remaining_settlement -= applied
        if entry.remaining_rial == 0:
            entry.status = "settled"

    settlement = Settlement(
        person_id=payload.person_id,
        amount_rial=payload.amount_rial,
        jalali_date=payload.jalali_date,
        local_time=payload.local_time,
        note=payload.note,
    )
    db.add(settlement)
    db.commit()
    db.refresh(settlement)
    return settlement


def create_cheque(db: Session, payload: ChequeCreate) -> Cheque:
    if payload.person_id is not None:
        _person_or_404(db, payload.person_id)
    cheque = Cheque(
        cheque_type=payload.cheque_type,
        person_id=payload.person_id,
        bank_name=payload.bank_name,
        cheque_number=payload.cheque_number,
        amount_rial=payload.amount_rial,
        issue_jalali_date=payload.issue_jalali_date,
        due_jalali_date=payload.due_jalali_date,
        note=payload.note,
    )
    db.add(cheque)
    db.flush()
    db.add(
        ChequeEvent(
            cheque_id=cheque.id,
            event_type="created",
            jalali_date=payload.issue_jalali_date,
            local_time=payload.local_time,
            note=payload.note,
        )
    )
    db.commit()
    return _cheque_or_404(db, cheque.id)


def add_cheque_event(db: Session, cheque_id: int, payload: ChequeEventCreate) -> Cheque:
    cheque = _cheque_or_404(db, cheque_id)
    if cheque.status == "canceled":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Canceled cheque cannot be changed.")
    cheque.status = payload.event_type
    if payload.event_type == "canceled":
        cheque.is_active = False
    db.add(
        ChequeEvent(
            cheque_id=cheque.id,
            event_type=payload.event_type,
            jalali_date=payload.jalali_date,
            local_time=payload.local_time,
            note=payload.note,
        )
    )
    db.commit()
    return _cheque_or_404(db, cheque.id)


def list_cheques(db: Session) -> list[Cheque]:
    return list(
        db.scalars(
            select(Cheque)
            .options(selectinload(Cheque.events))
            .order_by(Cheque.due_jalali_date, Cheque.id)
        )
    )


def get_dues(db: Session, jalali_date_to: str) -> DuesRead:
    open_ledger_entries = list(
        db.scalars(
            select(LedgerEntry)
            .where(
                LedgerEntry.status == "open",
                LedgerEntry.remaining_rial > 0,
                LedgerEntry.jalali_date <= jalali_date_to,
                LedgerEntry.is_active.is_(True),
            )
            .order_by(LedgerEntry.jalali_date, LedgerEntry.local_time, LedgerEntry.id)
        )
    )
    pending_cheques = list(
        db.scalars(
            select(Cheque)
            .options(selectinload(Cheque.events))
            .where(
                Cheque.status == "pending",
                Cheque.due_jalali_date <= jalali_date_to,
                Cheque.is_active.is_(True),
            )
            .order_by(Cheque.due_jalali_date, Cheque.id)
        )
    )
    return DuesRead(
        jalali_date_to=jalali_date_to,
        open_ledger_entries=open_ledger_entries,
        pending_cheques=pending_cheques,
    )
