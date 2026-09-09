import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.scripts import scheduled_backup
from app.scripts.scheduled_backup import run_scheduled_backup, write_status_atomic
from app.scripts.sqlite_backup import create_bundle


def _data(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "data" / "store.db"
    media = tmp_path / "data" / "media"
    source.parent.mkdir()
    (media / "products").mkdir(parents=True)
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, image_filename TEXT)")
        connection.execute("INSERT INTO products (image_filename) VALUES ('one.png')")
    (media / "products" / "one.png").write_bytes(b"image")
    return source, media


def test_scheduled_backup_success_writes_monitorable_status(tmp_path: Path) -> None:
    source, media = _data(tmp_path)
    destination = tmp_path / "backups"
    status_file = destination / "status.json"

    result = run_scheduled_backup(
        source=source,
        media_root=media,
        destination=destination,
        status_file=status_file,
        keep_days=30,
        keep_last=2,
    )

    status = json.loads(status_file.read_text(encoding="utf-8"))
    assert result == 0
    assert status["state"] == "success"
    assert status["bundle_name"].startswith("store-bundle-")
    assert status["media_files"] == 1
    assert status["referenced_product_images"] == 1
    assert (destination / status["bundle_name"]).is_dir()
    assert not list(destination.glob(".*.tmp"))


def test_scheduled_backup_failure_is_sanitized_and_returns_nonzero(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    source, media = _data(tmp_path)
    status_file = tmp_path / "monitor" / "status.json"
    secret = "BALE_BOT_TOKEN=never-print-this"

    def fail_bundle(*_args, **_kwargs):
        raise RuntimeError(secret)

    monkeypatch.setattr(scheduled_backup, "create_bundle", fail_bundle)
    result = run_scheduled_backup(
        source=source,
        media_root=media,
        destination=tmp_path / "backups",
        status_file=status_file,
        keep_days=30,
        keep_last=2,
    )

    status_text = status_file.read_text(encoding="utf-8")
    output = capsys.readouterr()
    assert result == 1
    assert json.loads(status_text)["state"] == "failure"
    assert json.loads(status_text)["error_code"] == "RuntimeError"
    assert secret not in status_text + output.out + output.err
    assert not list(status_file.parent.glob(".*.tmp"))


def test_status_writer_publishes_complete_json_with_atomic_replace(tmp_path: Path, monkeypatch) -> None:
    status_file = tmp_path / "status.json"
    replacements: list[tuple[Path, Path, str]] = []
    real_replace = os.replace

    def observed_replace(source, target):
        source_path = Path(source)
        replacements.append((source_path, Path(target), source_path.read_text(encoding="utf-8")))
        return real_replace(source, target)

    monkeypatch.setattr(scheduled_backup.os, "replace", observed_replace)
    write_status_atomic(status_file, {"schema_version": 1, "state": "success"})

    assert len(replacements) == 1
    assert replacements[0][0].name.startswith(".status.json.")
    assert replacements[0][1] == status_file
    assert json.loads(replacements[0][2])["state"] == "success"
    assert json.loads(status_file.read_text(encoding="utf-8"))["state"] == "success"


def test_scheduled_backup_prunes_old_valid_bundle_only_after_success(tmp_path: Path) -> None:
    source, media = _data(tmp_path)
    destination = tmp_path / "backups"
    old = create_bundle(source, media, destination, now=datetime(2025, 1, 1, tzinfo=timezone.utc))
    unrelated = destination / "store-bundle-customer-files"
    unrelated.mkdir()

    result = run_scheduled_backup(
        source=source,
        media_root=media,
        destination=destination,
        status_file=destination / "status.json",
        keep_days=30,
        keep_last=1,
    )

    status = json.loads((destination / "status.json").read_text(encoding="utf-8"))
    assert result == 0
    assert status["pruned_bundle_names"] == [old.name]
    assert not old.exists()
    assert unrelated.is_dir()


def test_scheduled_backup_does_not_prune_when_creation_fails(tmp_path: Path, monkeypatch) -> None:
    source, media = _data(tmp_path)
    destination = tmp_path / "backups"
    old = create_bundle(source, media, destination, now=datetime(2025, 1, 1, tzinfo=timezone.utc))
    monkeypatch.setattr(scheduled_backup, "create_bundle", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("fail")))

    result = run_scheduled_backup(
        source=source,
        media_root=media,
        destination=destination,
        status_file=destination / "status.json",
        keep_days=30,
        keep_last=1,
    )

    assert result == 1
    assert old.is_dir()


@pytest.mark.parametrize(
    ("keep_days", "keep_last", "lock_timeout"),
    [(0, 1, 10.0), (30, 0, 10.0), (30, 1, 0.0)],
)
def test_invalid_schedule_settings_fail_before_creating_a_bundle(
    tmp_path: Path, keep_days: int, keep_last: int, lock_timeout: float
) -> None:
    source, media = _data(tmp_path)
    destination = tmp_path / "backups"
    status_file = destination / "status.json"

    result = run_scheduled_backup(
        source=source,
        media_root=media,
        destination=destination,
        status_file=status_file,
        keep_days=keep_days,
        keep_last=keep_last,
        lock_timeout=lock_timeout,
    )

    assert result == 1
    assert json.loads(status_file.read_text(encoding="utf-8"))["error_code"] == "ValueError"
    assert not list(destination.glob("store-bundle-*"))


def test_unexpected_failure_is_sanitized_and_monitorable(tmp_path: Path, monkeypatch, capsys) -> None:
    source, media = _data(tmp_path)
    destination = tmp_path / "backups"
    status_file = destination / "status.json"
    secret = "unexpected-secret-value"

    class UnexpectedBackupError(Exception):
        pass

    def fail_unexpectedly(*_args, **_kwargs):
        raise UnexpectedBackupError(secret)

    monkeypatch.setattr(scheduled_backup, "create_bundle", fail_unexpectedly)
    result = run_scheduled_backup(
        source=source,
        media_root=media,
        destination=destination,
        status_file=status_file,
        keep_days=30,
        keep_last=7,
    )

    status_text = status_file.read_text(encoding="utf-8")
    output = capsys.readouterr()
    assert result == 1
    assert json.loads(status_text)["error_code"] == "UnexpectedBackupError"
    assert secret not in status_text + output.out + output.err
