"""Start an isolated browser-QA backend. Never points at backend/store.db."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = Path(os.environ.get("E2E_RUNTIME_ROOT", "")).resolve()
DATABASE_PATH = RUNTIME_ROOT / "store-e2e.db"
MEDIA_ROOT = RUNTIME_ROOT / "media"


def _validate_runtime_path() -> None:
    if (
        RUNTIME_ROOT.parent != Path(tempfile.gettempdir()).resolve()
        or re.fullmatch(r"store-admin-e2e-[a-f0-9]{12}", RUNTIME_ROOT.name) is None
    ):
        raise RuntimeError(f"Unsafe E2E runtime path: {RUNTIME_ROOT}")
    expected_url = f"sqlite:///{DATABASE_PATH.as_posix()}"
    if os.environ.get("DATABASE_URL") != expected_url:
        raise RuntimeError("E2E DATABASE_URL must point to store-e2e.db inside the validated OS temp runtime")
    configured_media = Path(os.environ.get("MEDIA_ROOT", "")).resolve()
    if configured_media != MEDIA_ROOT:
        raise RuntimeError("E2E MEDIA_ROOT must point inside the validated OS temp runtime")


def main() -> None:
    _validate_runtime_path()
    if RUNTIME_ROOT.exists():
        shutil.rmtree(RUNTIME_ROOT)
    RUNTIME_ROOT.mkdir(parents=True)
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND_ROOT, check=True)
    subprocess.run([sys.executable, "-m", "app.scripts.seed_demo"], cwd=BACKEND_ROOT, check=True)

    sys.path.insert(0, str(BACKEND_ROOT))
    from app.core.security import get_password_hash
    from app.db.session import SessionLocal
    from app.models.user import User

    with SessionLocal() as db:
        if db.query(User).filter(User.username == "e2e-operator").first() is None:
            db.add(User(username="e2e-operator", full_name="کاربر تست موبایل", hashed_password=get_password_hash("e2e-operator-password"), is_active=True, is_superuser=False, can_sales=True, can_catalog_inventory=True))
            db.commit()

    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8013, app_dir=str(BACKEND_ROOT), log_level="warning")


if __name__ == "__main__":
    main()
