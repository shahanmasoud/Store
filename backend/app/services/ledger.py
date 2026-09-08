from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from datetime import datetime, timezone

from app.core.time import utc_now
from app.models.ledger import Cheque, ChequeAudit, ChequeEvent, LedgerActionAudit, LedgerDueAudit, LedgerEntry, Person, Settlement
from app.models.user import User
from app.schemas.ledger import (
    ChequeCreate,
    ChequeEventCreate,
    ChequeUpdate,
    DueReminderGroup,
    DueReminderItem,
    DueRemindersRead,
    DueReminderTotals,
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


def _person_snapshot(person: Person) -> dict:
    return {"id": person.id, "name": person.name, "phone": person.phone, "person_type": person.person_type, "note": person.note, "credit_status": person.credit_status, "is_active": person.is_active}


def _entry_snapshot(entry: LedgerEntry) -> dict:
    return {"id": entry.id, "person_id": entry.person_id, "entry_type": entry.entry_type, "amount_rial": entry.amount_rial, "remaining_rial": entry.remaining_rial, "source_type": entry.source_type, "source_id": entry.source_id, "jalali_date": entry.jalali_date, "due_jalali_date": entry.due_jalali_date, "local_time": entry.local_time, "description": entry.description, "status": entry.status, "is_active": entry.is_active}


def _settlement_snapshot(settlement: Settlement) -> dict:
    return {"id": settlement.id, "person_id": settlement.person_id, "entry_type": settlement.entry_type, "amount_rial": settlement.amount_rial, "jalali_date": settlement.jalali_date, "local_time": settlement.local_time, "note": settlement.note}


def _audit_ledger(db: Session, *, entity_type: str, entity_id: int, action: str, actor: User, before: dict | None, after: dict | None, reason: str | None = None) -> None:
    db.add(LedgerActionAudit(entity_type=entity_type, entity_id=entity_id, action=action, actor_user_id=actor.id, actor_username=actor.username, actor_full_name=actor.full_name, before_json=before, after_json=after, reason=reason))


def create_person(db: Session, payload: PersonCreate, actor: User) -> Person:
    person = Person(
        name=payload.name,
        phone=payload.phone,
        person_type=payload.person_type,
        note=payload.note,
        credit_status=payload.credit_status,
    )
    db.add(person)
    db.flush()
    _audit_ledger(db, entity_type="person", entity_id=person.id, action="create", actor=actor, before=None, after=_person_snapshot(person), reason="ثبت شخص")
    db.commit()
    db.refresh(person)
    return person


def list_persons(db: Session, *, include_inactive: bool = False) -> list[Person]:
    statement = select(Person)
    if not include_inactive:
        statement = statement.where(Person.is_active.is_(True))
    return list(db.scalars(statement.order_by(Person.name, Person.id)))


def update_person(db: Session, person_id: int, payload: PersonUpdate, actor: User) -> Person:
    person = _person_or_404(db, person_id)
    before = _person_snapshot(person)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(person, field, value)
    _audit_ledger(db, entity_type="person", entity_id=person.id, action="update", actor=actor, before=before, after=_person_snapshot(person), reason="ویرایش مشخصات شخص")
    db.commit()
    db.refresh(person)
    return person


def deactivate_person(db: Session, person_id: int, actor: User) -> None:
    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="شخص پیدا نشد.")
    if person.is_active:
        before = _person_snapshot(person)
        person.is_active = False
        _audit_ledger(db, entity_type="person", entity_id=person.id, action="deactivate", actor=actor, before=before, after=_person_snapshot(person), reason="غیرفعال‌سازی شخص")
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


def create_manual_entry(db: Session, payload: LedgerEntryCreate, actor: User) -> LedgerEntry:
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
    db.flush()
    _audit_ledger(db, entity_type="ledger_entry", entity_id=entry.id, action="create", actor=actor, before=None, after=_entry_snapshot(entry), reason=payload.description or "ثبت سند دستی")
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


def create_settlement(db: Session, payload: SettlementCreate, actor: User) -> Settlement:
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
    db.flush()
    _audit_ledger(db, entity_type="settlement", entity_id=settlement.id, action="create", actor=actor, before=None, after=_settlement_snapshot(settlement), reason=payload.note or "ثبت تسویه")
    db.commit()
    db.refresh(settlement)
    return settlement


def _cheque_snapshot(cheque: Cheque) -> dict:
    return {
        "id": cheque.id,
        "cheque_type": cheque.cheque_type,
        "person_id": cheque.person_id,
        "bank_name": cheque.bank_name,
        "cheque_number": cheque.cheque_number,
        "amount_rial": cheque.amount_rial,
        "issue_jalali_date": cheque.issue_jalali_date,
        "due_jalali_date": cheque.due_jalali_date,
        "status": cheque.status,
        "note": cheque.note,
        "is_active": cheque.is_active,
    }


def _audit_cheque(
    db: Session,
    cheque: Cheque,
    *,
    action: str,
    actor: User,
    before: dict | None,
    after: dict | None,
    reason: str,
) -> None:
    db.add(
        ChequeAudit(
            cheque_id=cheque.id,
            action=action,
            actor_user_id=actor.id,
            actor_username=actor.username,
            actor_full_name=actor.full_name,
            before_json=before,
            after_json=after,
            reason=reason,
        )
    )


def _normalized_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def create_cheque(db: Session, payload: ChequeCreate, actor: User) -> Cheque:
    if payload.person_id is not None:
        _person_or_404(db, payload.person_id)
    now = utc_now()
    cheque = Cheque(
        cheque_type=payload.cheque_type,
        person_id=payload.person_id,
        bank_name=payload.bank_name,
        cheque_number=payload.cheque_number,
        amount_rial=payload.amount_rial,
        issue_jalali_date=payload.issue_jalali_date,
        due_jalali_date=payload.due_jalali_date,
        note=payload.note,
        updated_at_utc=now,
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
    _audit_cheque(
        db,
        cheque,
        action="create",
        actor=actor,
        before=None,
        after=_cheque_snapshot(cheque),
        reason="ثبت اولیه چک",
    )
    db.commit()
    return _cheque_or_404(db, cheque.id)


def update_cheque(db: Session, cheque_id: int, payload: ChequeUpdate, actor: User) -> Cheque:
    cheque = _cheque_or_404(db, cheque_id)
    if not cheque.is_active or cheque.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="فقط چک فعال و در انتظار قابل ویرایش است.",
        )
    if cheque.updated_at_utc is None or _normalized_utc(cheque.updated_at_utc) != _normalized_utc(payload.expected_updated_at):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="این چک پس از باز شدن فرم تغییر کرده است؛ اطلاعات را دوباره دریافت کنید.",
        )

    changes = payload.model_dump(
        exclude_unset=True,
        exclude={"reason", "expected_updated_at"},
    )
    if "person_id" in changes and changes["person_id"] is not None:
        _person_or_404(db, changes["person_id"])
    final_issue_date = changes.get("issue_jalali_date", cheque.issue_jalali_date)
    final_due_date = changes.get("due_jalali_date", cheque.due_jalali_date)
    if final_issue_date is None or final_due_date is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="تاریخ صدور و سررسید الزامی است.")
    if final_due_date < final_issue_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="تاریخ سررسید نمی‌تواند پیش از تاریخ صدور باشد.",
        )
    if not changes or all(getattr(cheque, field) == value for field, value in changes.items()):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="هیچ تغییری برای ثبت وجود ندارد.")

    before = _cheque_snapshot(cheque)
    for field, value in changes.items():
        setattr(cheque, field, value)
    cheque.updated_at_utc = utc_now()
    _audit_cheque(
        db,
        cheque,
        action="update",
        actor=actor,
        before=before,
        after=_cheque_snapshot(cheque),
        reason=payload.reason,
    )
    db.commit()
    return _cheque_or_404(db, cheque.id)


def add_cheque_event(db: Session, cheque_id: int, payload: ChequeEventCreate, actor: User) -> Cheque:
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
    before = _cheque_snapshot(cheque)
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
    cheque.updated_at_utc = utc_now()
    _audit_cheque(
        db,
        cheque,
        action="event",
        actor=actor,
        before=before,
        after=_cheque_snapshot(cheque),
        reason=(payload.note.strip() if payload.note and payload.note.strip() else f"ثبت رویداد {payload.event_type}"),
    )
    db.commit()
    return _cheque_or_404(db, cheque.id)


def list_cheque_audits(db: Session, cheque_id: int) -> list[ChequeAudit]:
    _cheque_or_404(db, cheque_id)
    return list(
        db.scalars(
            select(ChequeAudit)
            .where(ChequeAudit.cheque_id == cheque_id)
            .order_by(ChequeAudit.occurred_at_utc, ChequeAudit.id)
        )
    )


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


def _reminder_totals(items: list[DueReminderItem]) -> DueReminderTotals:
    receivables = [item for item in items if item.direction == "receivable"]
    payables = [item for item in items if item.direction == "payable"]
    return DueReminderTotals(
        count=len(items),
        total_rial=sum(item.amount_rial for item in items),
        receivable_count=len(receivables),
        receivable_total_rial=sum(item.amount_rial for item in receivables),
        payable_count=len(payables),
        payable_total_rial=sum(item.amount_rial for item in payables),
    )


def _reminder_group(items: list[DueReminderItem]) -> DueReminderGroup:
    return DueReminderGroup(items=items, **_reminder_totals(items).model_dump())


def get_due_reminders(db: Session, today_jalali: str, through_jalali: str) -> DueRemindersRead:
    ledger_rows = db.execute(
        select(LedgerEntry, Person.name)
        .join(Person, Person.id == LedgerEntry.person_id)
        .where(
            LedgerEntry.is_active.is_(True),
            LedgerEntry.status == "open",
            LedgerEntry.remaining_rial > 0,
            LedgerEntry.due_jalali_date.is_not(None),
            LedgerEntry.due_jalali_date <= through_jalali,
        )
    ).all()
    cheque_rows = db.execute(
        select(Cheque, Person.name)
        .outerjoin(Person, Person.id == Cheque.person_id)
        .where(
            Cheque.is_active.is_(True),
            Cheque.status == "pending",
            Cheque.due_jalali_date <= through_jalali,
        )
    ).all()

    items = [
        DueReminderItem(
            kind="ledger_entry",
            record_id=entry.id,
            person_id=entry.person_id,
            person_name=person_name,
            direction="receivable" if entry.entry_type == "debit" else "payable",
            record_type=entry.entry_type,
            amount_rial=entry.remaining_rial,
            due_jalali_date=entry.due_jalali_date,
            status=entry.status,
            description=entry.description,
            cheque_number=None,
            bank_name=None,
        )
        for entry, person_name in ledger_rows
    ]
    items.extend(
        DueReminderItem(
            kind="cheque",
            record_id=cheque.id,
            person_id=cheque.person_id,
            person_name=person_name,
            direction="receivable" if cheque.cheque_type == "received" else "payable",
            record_type=cheque.cheque_type,
            amount_rial=cheque.amount_rial,
            due_jalali_date=cheque.due_jalali_date,
            status=cheque.status,
            description=cheque.note,
            cheque_number=cheque.cheque_number,
            bank_name=cheque.bank_name,
        )
        for cheque, person_name in cheque_rows
    )
    items.sort(key=lambda item: (item.due_jalali_date, item.kind, item.record_id))
    overdue = [item for item in items if item.due_jalali_date < today_jalali]
    today = [item for item in items if item.due_jalali_date == today_jalali]
    upcoming = [item for item in items if today_jalali < item.due_jalali_date <= through_jalali]
    return DueRemindersRead(
        today_jalali=today_jalali,
        through_jalali=through_jalali,
        overdue=_reminder_group(overdue),
        today=_reminder_group(today),
        upcoming=_reminder_group(upcoming),
        totals=_reminder_totals(items),
    )
