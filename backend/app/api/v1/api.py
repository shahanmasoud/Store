from fastapi import APIRouter

from app.api.v1 import auth
from app.api.v1 import catalog
from app.api.v1 import sales

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(catalog.router, tags=["catalog"])
api_router.include_router(sales.router, tags=["sales"])

