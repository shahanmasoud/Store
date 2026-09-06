import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.scripts.sqlite_backup import (
    create_backup,
    prune_backups,
    restore_backup,
    sqlite_path_from_url,
    verify_backup,
)


def _database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE entries (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("INSERT INTO entries (value) VALUES ('financial-data')")


def test_backup_verify_and_restore(tmp_path: Path) -> None:
    source = tmp_path / "source.db"
    _database(source)

    backup = create_backup(source, tmp_path / "backups")
    checksum = verify_backup(backup)
    assert len(checksum) == 64
    assert backup.with_suffix(".db.sha256").is_file()

    restored = restore_backup(backup, tmp_path / "restored" / "store.db")
    with sqlite3.connect(restored) as connection:
        assert connection.execute("SELECT value FROM entries").fetchone() == ("financial-data",)


def test_restore_refuses_to_replace_without_explicit_flag(tmp_path: Path) -> None:
    source = tmp_path / "source.db"
    target = tmp_path / "target.db"
    _database(source)
    _database(target)
    backup = create_backup(source, tmp_path / "backups")

    with pytest.raises(FileExistsError):
        restore_backup(backup, target)


def test_verify_detects_tampering(tmp_path: Path) -> None:
    source = tmp_path / "source.db"
    _database(source)
    backup = create_backup(source, tmp_path / "backups")
    with backup.open("ab") as stream:
        stream.write(b"tampered")

    with pytest.raises(RuntimeError, match="checksum"):
        verify_backup(backup)


def test_retention_only_removes_matching_old_backups(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backups"
    source = tmp_path / "source.db"
    _database(source)
    old_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    old_backup = create_backup(source, backup_dir, now=old_time)
    unrelated = backup_dir / "customer-file.db"
    unrelated.write_bytes(b"keep")
    old_timestamp = (old_time - timedelta(days=1)).timestamp()
    os.utime(old_backup, (old_timestamp, old_timestamp))

    removed = prune_backups(backup_dir, 7, now=datetime(2026, 2, 1, tzinfo=timezone.utc))

    assert removed == [old_backup]
    assert not old_backup.exists()
    assert not old_backup.with_suffix(".db.sha256").exists()
    assert unrelated.exists()


@pytest.mark.parametrize(
    ("url", "suffix"),
    [("sqlite:///./store.db", "store.db"), ("sqlite:////home/user/store.db", "/home/user/store.db")],
)
def test_sqlite_path_from_url(url: str, suffix: str) -> None:
    assert sqlite_path_from_url(url).as_posix().endswith(suffix)


def test_sqlite_path_rejects_memory_and_other_engines() -> None:
    with pytest.raises(ValueError):
        sqlite_path_from_url("sqlite:///:memory:")
    with pytest.raises(ValueError):
        sqlite_path_from_url("postgresql://localhost/store")
