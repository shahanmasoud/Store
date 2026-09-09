import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.core.config import get_settings


def test_0019_migration_preserves_legacy_ledger_rows_without_backfill(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "legacy-sale-ledger.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    get_settings.cache_clear()
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "0018_payment_due_audits")

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """INSERT INTO persons
               (id, name, phone, person_type, note, credit_status, is_active, created_at_utc, updated_at_utc)
               VALUES (1, 'legacy customer', NULL, 'customer', NULL, 'normal', 1, CURRENT_TIMESTAMP, NULL)"""
        )
        connection.execute(
            """INSERT INTO ledger_entries
               (id, person_id, entry_type, amount_rial, remaining_rial, source_type, source_id,
                jalali_date, due_jalali_date, local_time, description, status, is_active,
                created_at_utc, updated_at_utc)
               VALUES (1, 1, 'debit', 900000, 650000, 'sale', 77,
                       '1405/06/01', NULL, '10:00', 'legacy exact row', 'open', 1,
                       CURRENT_TIMESTAMP, NULL)"""
        )
        before = connection.execute(
            "SELECT id, person_id, amount_rial, remaining_rial, source_type, source_id, description FROM ledger_entries"
        ).fetchall()

    command.upgrade(config, "head")

    with sqlite3.connect(database_path) as connection:
        after = connection.execute(
            "SELECT id, person_id, amount_rial, remaining_rial, source_type, source_id, description FROM ledger_entries"
        ).fetchall()
        allocation_table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='settlement_allocations'"
        ).fetchone()
        unique_index_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' AND name='uq_ledger_entries_sale_source'"
        ).fetchone()[0]
    assert after == before
    assert allocation_table == ("settlement_allocations",)
    assert "UNIQUE INDEX" in unique_index_sql.upper()
    assert "SOURCE_TYPE = 'SALE'" in unique_index_sql.upper()
    get_settings.cache_clear()
