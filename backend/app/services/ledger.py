from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.ledger import Cheque, ChequeEvent, LedgerDueAudit, LedgerEntry, Person, Settlement
from app.models.user import User
from app.schemas.ledger import (
    ChequeCreate,
    ChequeEventCreate,
    DuesRead,
    LedgerEntryCreate,
    LedgerDueDateUpdate,
    PersonCreate,
    PersonUpdate,
    SettlementCreate,
)


def _person_or_404(db: Session, person_id: int) -> Person:
    person = db.get(Person, person_id)
    if not person or not person.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="شخص پیدا نشد.")
    return person


def _cheque_or_404(db: Session, cheque_id: int) -> Cheque:
    cheque = db.scalar(
        select(Cheque)
        .options(selectinload(Cheque.events))
        .where(Cheque.id == cheque_id)
    )
    if not cheque:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="چک پیدا نشد.")
    return cheque


def create_person(db: Session, payload: PersonCreate) -> Person:
    person = Person(
        name=payload.name,
        phone=payload.phone,
        person_type=payload.person_type,
        note=payload.note,
        credit_status=payload.credit_status,
    )
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


def list_persons(db: Session, *, include_inactive: bool = False) -> list[Person]:
    statement = select(Person)
    if not include_inactive:
        statement = statement.where(Person.is_active.is_(True))
    return list(db.scalars(statement.order_by(Person.name, Person.id)))


def update_person(db: Session, person_id: int, payload: PersonUpdate) -> Person:
    person = _person_or_404(db, person_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(person, field, value)
    db.commit()
    db.refresh(person)
    return person


def deactivate_person(db: Session, person_id: int) -> None:
    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="شخص پیدا نشد.")
    if person.is_active:
        person.is_active = False
        db.commit()


def get_person_account_summary(db: Session, person_id: int) -> dict[str, int]:
    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="شخص پیدا نشد.")
    totals = dict(
        db.execute(
            select(LedgerEntry.entry_type, func.coalesce(func.sum(LedgerEntry.remaining_rial), 0))
            .where(
                LedgerEntry.person_id == person_id,
                LedgerEntry.is_active.is_(True),
                LedgerEntry.status == "open",
                LedgerEntry.remaining_rial > 0,
            )
            .group_by(LedgerEntry.entry_type)
        ).all()
    )
    debit = int(totals.get("debit", 0))
    credit = int(totals.get("credit", 0))
    net = debit - credit
    open_entries_count = int(
        db.scalar(
            select(func.count(LedgerEntry.id)).where(
                LedgerEntry.person_id == person_id,
                LedgerEntry.is_active.is_(True),
                LedgerEntry.status == "open",
                LedgerEntry.remaining_rial > 0,
            )
        )
        or 0
    )
    return {
        "person_id": person_id,
        "debit_open_rial": debit,
        "credit_open_rial": credit,
        "net_balance_rial": net,
        "open_entries_count": open_entries_count,
    }


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
        due_jalali_date=payload.due_jalali_date,
        local_time=payload.local_time,
        description=payload.description,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_person_ledger(db: Session, person_id: int) -> list[LedgerEntry]:
    if not db.get(Person, person_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="شخص پیدا نشد.")
    return list(
        db.scalars(
            select(LedgerEntry)
            .where(LedgerEntry.person_id == person_id, LedgerEntry.is_active.is_(True))
            .order_by(LedgerEntry.jalali_date, LedgerEntry.local_time, LedgerEntry.id)
        )
    )


def _ledger_entry_or_404(db: Session, entry_id: int) -> LedgerEntry:
    entry = db.get(LedgerEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="سند حساب پیدا نشد.")
    return entry


def update_manual_entry_due_date(
    db: Session,
    entry_id: int,
    payload: LedgerDueDateUpdate,
    actor: User,
) -> LedgerEntry:
    entry = _ledger_entry_or_404(db, entry_id)
    if (
        entry.source_type != "manual"
        or not entry.is_active
        or entry.status != "open"
        or entry.remaining_rial <= 0
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="فقط سررسید سند دستیِ باز و فعال قابل تغییر است.",
        )
    if entry.due_jalali_date == payload.due_jalali_date:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="سررسید جدید با مقدار فعلی یکسان است.")

    before_due_date = entry.due_jalali_date
    entry.due_jalali_date = payload.due_jalali_date
    db.add(
        LedgerDueAudit(
            entry_id=entry.id,
            actor_user_id=actor.id,
            actor_username=actor.username,
            actor_full_name=actor.full_name,
            before_due_date=before_due_date,
            after_due_date=payload.due_jalali_date,
            reason=payload.reason,
        )
    )
    db.commit()
    db.refresh(entry)
    return entry


def list_ledger_due_audits(db: Session, entry_id: int) -> list[LedgerDueAudit]:
    _ledger_entry_or_404(db, entry_id)
    return list(
        db.scalars(
            select(LedgerDueAudit)
            .where(LedgerDueAudit.entry_id == entry_id)
            .order_by(LedgerDueAudit.occurred_at_utc, LedgerDueAudit.id)
        )
    )


def create_settlement(db: Session, payload: SettlementCreate) -> Settlement:
    _person_or_404(db, payload.person_id)
    open_entries = list(
        db.scalars(
            select(LedgerEntry)
            .where(
                LedgerEntry.person_id == payload.person_id,
                LedgerEntry.entry_type == payload.entry_type,
                LedgerEntry.status == "open",
                LedgerEntry.remaining_rial > 0,
                LedgerEntry.is_active.is_(True),
            )
            .order_by(LedgerEntry.jalali_date, LedgerEntry.local_time, LedgerEntry.id)
        )
    )
    open_balance = sum(entry.remaining_rial for entry in open_entries)
    if payload.amount_rial > open_balance:
        side = "بدهکار" if payload.entry_type == "debit" else "بستانکار"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"مبلغ تسویه از مانده {side} بیشتر است.",
        )

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
        entry_type=payload.entry_type,
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
    allowed_transitions = {
        "pending": {"cleared", "bounced", "canceled"},
        "bounced": {"cleared", "canceled"},
        "cleared": set(),
        "canceled": set(),
    }
    if payload.event_type not in allowed_transitions.get(cheque.status, set()):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="این تغییر وضعیت برای چک مجاز نیست.")
    latest_event = max(cheque.events, key=lambda item: (item.jalali_date, item.local_time, item.id), default=None)
    latest_moment = (latest_event.jalali_date, latest_event.local_time) if latest_event else (cheque.issue_jalali_date, "00:00")
    if (payload.jalali_date, payload.local_time) < latest_moment:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="تاریخ اقدام نمی‌تواند پیش از آخرین رویداد چک باشد.",
        )
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
                LedgerEntry.due_jalali_date.is_not(None),
                LedgerEntry.due_jalali_date <= jalali_date_to,
                LedgerEntry.is_active.is_(True),
            )
            .order_by(LedgerEntry.due_jalali_date, LedgerEntry.jalali_date, LedgerEntry.local_time, LedgerEntry.id)
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
