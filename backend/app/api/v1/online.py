from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.time import validate_jalali_date
from app.db.session import get_db
from app.models.online import OnlineChannel, OnlineOrder, OnlinePriceRule, StockReservation
from app.schemas.online import (
    OnlineCatalogItemRead,
    OnlineChannelCreate,
    OnlineChannelRead,
    OnlineOrderCreate,
    OnlineOrderRead,
    OnlinePriceRuleCreate,
    OnlinePriceRuleRead,
    StockReservationCreate,
    StockReservationRead,
)
from app.services import online as online_service

router = APIRouter()


def _optional_valid_date(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return validate_jalali_date(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def get_online_channel(
    x_online_token: str = Header(alias="X-Online-Token"),
    db: Session = Depends(get_db),
) -> OnlineChannel:
    return online_service.channel_from_token(db, x_online_token)


@router.get("/online/channels", response_model=list[OnlineChannelRead], dependencies=[Depends(get_current_user)])
def channels(db: Session = Depends(get_db)) -> list[OnlineChannel]:
    return online_service.list_channels(db)


@router.post(
    "/online/channels",
    response_model=OnlineChannelRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_user)],
)
def create_channel(payload: OnlineChannelCreate, db: Session = Depends(get_db)) -> OnlineChannel:
    return online_service.create_channel(db, payload)


@router.post(
    "/online/price-rules",
    response_model=OnlinePriceRuleRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_user)],
)
def create_price_rule(payload: OnlinePriceRuleCreate, db: Session = Depends(get_db)) -> OnlinePriceRule:
    return online_service.create_price_rule(db, payload)


@router.get(
    "/online/price-rules",
    response_model=list[OnlinePriceRuleRead],
    dependencies=[Depends(get_current_user)],
)
def price_rules(
    channel_id: int | None = None,
    variant_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[OnlinePriceRule]:
    return online_service.list_price_rules(db, channel_id, variant_id)


@router.post(
    "/online/reservations",
    response_model=StockReservationRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_user)],
)
def create_reservation(
    payload: StockReservationCreate,
    db: Session = Depends(get_db),
) -> StockReservation:
    return online_service.create_reservation(db, payload)


@router.get(
    "/online/reservations",
    response_model=list[StockReservationRead],
    dependencies=[Depends(get_current_user)],
)
def reservations(
    channel_id: int | None = None,
    variant_id: int | None = None,
    reservation_status: str | None = Query(default=None, alias="status"),
    as_of_jalali_date: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[StockReservationRead]:
    return online_service.list_reservations(
        db,
        channel_id,
        variant_id,
        reservation_status,
        _optional_valid_date(as_of_jalali_date),
    )


@router.get("/online/orders", response_model=list[OnlineOrderRead], dependencies=[Depends(get_current_user)])
def orders(
    channel_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[OnlineOrder]:
    return online_service.list_orders(db, channel_id)


@router.get("/online/public/catalog", response_model=list[OnlineCatalogItemRead])
def public_catalog(
    channel: OnlineChannel = Depends(get_online_channel),
    db: Session = Depends(get_db),
) -> list[OnlineCatalogItemRead]:
    return online_service.list_catalog(db, channel)


@router.post("/online/public/orders", response_model=OnlineOrderRead, status_code=status.HTTP_201_CREATED)
def public_create_order(
    payload: OnlineOrderCreate,
    channel: OnlineChannel = Depends(get_online_channel),
    db: Session = Depends(get_db),
) -> OnlineOrder:
    return online_service.create_order(db, channel, payload)
