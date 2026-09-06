from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.v1.api import api_router
from app.core.config import get_settings
from app.db.session import engine
from app.services.bale_poller import start_bale_poller, stop_bale_poller

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    start_bale_poller()
    try:
        yield
    finally:
        stop_bale_poller()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):51\d{2}$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)

frontend_dir = Path(__file__).resolve().parent / "frontend"
frontend_index = frontend_dir / "index.html"
frontend_assets = frontend_dir / "assets"

if frontend_index.is_file() and frontend_assets.is_dir():
    app.mount("/assets", StaticFiles(directory=frontend_assets), name="frontend-assets")

    @app.get("/", include_in_schema=False)
    def storefront() -> FileResponse:
        return FileResponse(frontend_index)

    @app.get("/admin", include_in_schema=False)
    def admin_frontend() -> FileResponse:
        return FileResponse(frontend_index)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


@app.get("/ready", tags=["system"])
def readiness_check() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ready", "database": "ok"}

