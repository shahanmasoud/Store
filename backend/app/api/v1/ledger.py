from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.v1.auth import require_any_permission, require_permission, require_superuser
from app.core.time import validate_jalali_date
from app.db.session import get_db
from app.schemas.ledger import (
    ChequeCreate,
    ChequeAuditRead,
    ChequeEventCreate,
    ChequePersonOption,
    ChequeRead,
    ChequeUpdate,
    DuesRead,
    DueRemindersRead,
    DueReminderKind,
    LedgerEntryCreate,
    LedgerEntryRead,
    LedgerDueAuditRead,
    LedgerDueDateUpdate,
    PersonCreate,
    PersonAccountSummary,
    PersonRead,
    PersonUpdate,
    SettlementCreate,
    SettlementRead,
)
from app.services import ledger as ledger_service

router = APIRouter()


@router.post("/persons", response_model=PersonRead, status_code=status.HTTP_201_CREATED)
def create_person(payload: PersonCreate, db: Session = Depends(get_db), actor=Depends(require_permission("can_ledger"))) -> PersonRead:
    return ledger_service.create_person(db, payload, actor)


@router.get("/persons", response_model=list[PersonRead])
def persons(include_inactive: bool = Query(False), db: Session = Depends(get_db), _=Depends(require_permission("can_ledger"))) -> list[PersonRead]:
    return ledger_service.list_persons(db, include_inactive=include_inactive)


@router.patch("/persons/{person_id}", response_model=PersonRead)
def update_person(
    person_id: int,
    payload: PersonUpdate,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("can_ledger")),
) -> PersonRead:
    return ledger_service.update_person(db, person_id, payload, actor)


@router.delete("/persons/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_person(
    person_id: int,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("can_ledger")),
) -> None:
    ledger_service.deactivate_person(db, person_id, actor)


@router.get("/ledger/persons/{person_id}/summary", response_model=PersonAccountSummary)
def person_account_summary(person_id: int, db: Session = Depends(get_db), _=Depends(require_permission("can_ledger"))) -> PersonAccountSummary:
    return ledger_service.get_person_account_summary(db, person_id)


@router.get("/ledger/persons/{person_id}", response_model=list[LedgerEntryRead])
def person_ledger(person_id: int, db: Session = Depends(get_db), _=Depends(require_permission("can_ledger"))) -> list[LedgerEntryRead]:
    return ledger_service.get_person_ledger(db, person_id)


@router.post("/ledger/manual-entry", response_model=LedgerEntryRead, status_code=status.HTTP_201_CREATED)
def create_manual_entry(payload: LedgerEntryCreate, db: Session = Depends(get_db), actor=Depends(require_permission("can_ledger"))) -> LedgerEntryRead:
    return ledger_service.create_manual_entry(db, payload, actor)


@router.patch("/ledger/entries/{entry_id}/due-date", response_model=LedgerEntryRead)
def update_ledger_entry_due_date(
    entry_id: int,
    payload: LedgerDueDateUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_permission("can_ledger")),
) -> LedgerEntryRead:
    return ledger_service.update_manual_entry_due_date(db, entry_id, payload, admin)


@router.get("/ledger/entries/{entry_id}/due-date/audits", response_model=list[LedgerDueAuditRead])
def ledger_entry_due_date_audits(
    entry_id: int,
    db: Session = Depends(get_db),
    _admin: object = Depends(require_permission("can_ledger")),
) -> list[LedgerDueAuditRead]:
    return ledger_service.list_ledger_due_audits(db, entry_id)


@router.post("/settlements", response_model=SettlementRead, status_code=status.HTTP_201_CREATED)
def create_settlement(payload: SettlementCreate, db: Session = Depends(get_db), actor=Depends(require_permission("can_ledger"))) -> SettlementRead:
    return ledger_service.create_settlement(db, payload, actor)


@router.get("/dues", response_model=DuesRead)
def dues(jalali_date_to: str = Query(...), db: Session = Depends(get_db), actor=Depends(require_any_permission("can_ledger", "can_cheques_reports"))) -> DuesRead:
    try:
        validated_date = validate_jalali_date(jalali_date_to)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ledger_service.get_dues(db, validated_date, include_ledger=actor.is_superuser or actor.can_ledger, include_cheques=actor.is_superuser or actor.can_cheques_reports)


@router.get("/due-reminders", response_model=DueRemindersRead)
def due_reminders(
    today_jalali: str = Query(...),
    through_jalali: str = Query(...),
    person_id: int | None = Query(default=None, gt=0),
    kind: DueReminderKind | None = Query(default=None),
    db: Session = Depends(get_db),
    actor=Depends(require_any_permission("can_sales", "can_ledger", "can_cheques_reports")),
) -> DueRemindersRead:
    try:
        today = validate_jalali_date(today_jalali)
        through = validate_jalali_date(through_jalali)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if through < today:
        raise HTTPException(status_code=422, detail="پایان بازه یادآوری نمی‌تواند پیش از امروز باشد.")
    return ledger_service.get_due_reminders(
        db,
        today,
        through,
        include_sales=actor.is_superuser or actor.can_sales,
        include_ledger=actor.is_superuser or actor.can_ledger,
        include_cheques=actor.is_superuser or actor.can_cheques_reports,
        person_id=person_id,
        kind=kind,
    )


@router.post("/cheques", response_model=ChequeRead, status_code=status.HTTP_201_CREATED)
def create_cheque(
    payload: ChequeCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_permission("can_cheques_reports")),
) -> ChequeRead:
    return ledger_service.create_cheque(db, payload, admin)


@router.patch("/cheques/{cheque_id}", response_model=ChequeRead)
def update_cheque(
    cheque_id: int,
    payload: ChequeUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_permission("can_cheques_reports")),
) -> ChequeRead:
    return ledger_service.update_cheque(db, cheque_id, payload, admin)


@router.post("/cheques/{cheque_id}/events", response_model=ChequeRead)
def create_cheque_event(
    cheque_id: int,
    payload: ChequeEventCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_permission("can_cheques_reports")),
) -> ChequeRead:
    return ledger_service.add_cheque_event(db, cheque_id, payload, admin)


@router.get("/cheques/{cheque_id}/audits", response_model=list[ChequeAuditRead])
def cheque_audits(
    cheque_id: int,
    db: Session = Depends(get_db),
    _admin: object = Depends(require_permission("can_cheques_reports")),
) -> list[ChequeAuditRead]:
    return ledger_service.list_cheque_audits(db, cheque_id)


@router.get("/cheques", response_model=list[ChequeRead])
def cheques(db: Session = Depends(get_db), _=Depends(require_permission("can_cheques_reports"))) -> list[ChequeRead]:
    return ledger_service.list_cheques(db)


@router.get("/cheques/form-options", response_model=list[ChequePersonOption])
def cheque_form_options(db: Session = Depends(get_db), _=Depends(require_permission("can_cheques_reports"))) -> list[ChequePersonOption]:
    return ledger_service.list_persons(db, include_inactive=False)
