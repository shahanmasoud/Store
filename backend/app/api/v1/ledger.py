from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.time import validate_jalali_date
from app.db.session import get_db
from app.schemas.ledger import (
    ChequeCreate,
    ChequeEventCreate,
    ChequeRead,
    DuesRead,
    LedgerEntryCreate,
    LedgerEntryRead,
    PersonCreate,
    PersonRead,
    SettlementCreate,
    SettlementRead,
)
from app.services import ledger as ledger_service

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.post("/persons", response_model=PersonRead, status_code=status.HTTP_201_CREATED)
def create_person(payload: PersonCreate, db: Session = Depends(get_db)) -> PersonRead:
    return ledger_service.create_person(db, payload)


@router.get("/persons", response_model=list[PersonRead])
def persons(db: Session = Depends(get_db)) -> list[PersonRead]:
    return ledger_service.list_persons(db)


@router.get("/ledger/persons/{person_id}", response_model=list[LedgerEntryRead])
def person_ledger(person_id: int, db: Session = Depends(get_db)) -> list[LedgerEntryRead]:
    return ledger_service.get_person_ledger(db, person_id)


@router.post("/ledger/manual-entry", response_model=LedgerEntryRead, status_code=status.HTTP_201_CREATED)
def create_manual_entry(payload: LedgerEntryCreate, db: Session = Depends(get_db)) -> LedgerEntryRead:
    return ledger_service.create_manual_entry(db, payload)


@router.post("/settlements", response_model=SettlementRead, status_code=status.HTTP_201_CREATED)
def create_settlement(payload: SettlementCreate, db: Session = Depends(get_db)) -> SettlementRead:
    return ledger_service.create_settlement(db, payload)


@router.get("/dues", response_model=DuesRead)
def dues(jalali_date_to: str = Query(...), db: Session = Depends(get_db)) -> DuesRead:
    try:
        validated_date = validate_jalali_date(jalali_date_to)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ledger_service.get_dues(db, validated_date)


@router.post("/cheques", response_model=ChequeRead, status_code=status.HTTP_201_CREATED)
def create_cheque(payload: ChequeCreate, db: Session = Depends(get_db)) -> ChequeRead:
    return ledger_service.create_cheque(db, payload)


@router.post("/cheques/{cheque_id}/events", response_model=ChequeRead)
def create_cheque_event(cheque_id: int, payload: ChequeEventCreate, db: Session = Depends(get_db)) -> ChequeRead:
    return ledger_service.add_cheque_event(db, cheque_id, payload)


@router.get("/cheques", response_model=list[ChequeRead])
def cheques(db: Session = Depends(get_db)) -> list[ChequeRead]:
    return ledger_service.list_cheques(db)
