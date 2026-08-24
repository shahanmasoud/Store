from fastapi import APIRouter

from app.api.v1 import auth
from app.api.v1 import catalog
from app.api.v1 import ledger
from app.api.v1 import online
from app.api.v1 import purchases
from app.api.v1 import reports
from app.api.v1 import sales

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(catalog.router, tags=["catalog"])
api_router.include_router(ledger.router, tags=["ledger"])
api_router.include_router(online.router, tags=["online"])
api_router.include_router(purchases.router, tags=["purchases"])
api_router.include_router(reports.router, tags=["reports"])
api_router.include_router(sales.router, tags=["sales"])

