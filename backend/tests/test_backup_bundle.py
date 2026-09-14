import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.scripts import sqlite_backup
from app.scripts.sqlite_backup import create_bundle, prune_bundles, restore_bundle, verify_bundle
from app.services.data_lock import data_lock_path, exclusive_data_lock


def _store_database(path: Path, image_filename: str | None = "lentil.png") -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT NOT NULL, image_filename TEXT)"
        )
        connection.execute(
            "CREATE TABLE ledger_entries (id INTEGER PRIMARY KEY, amount INTEGER NOT NULL)"
        )
        connection.execute("INSERT INTO products (name, image_filename) VALUES ('lentil', ?)", (image_filename,))
        connection.execute("INSERT INTO ledger_entries (amount) VALUES (125000)")


def _store_data(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "data" / "store.db"
    media = tmp_path / "data" / "media"
    source.parent.mkdir()
    (media / "products").mkdir(parents=True)
    _store_database(source)
    (media / "products" / "lentil.png").write_bytes(b"valid-image-bytes")
    (media / "notes.txt").write_text("backup me", encoding="utf-8")
    return source, media


def test_bundle_round_trip_contains_database_media_manifest_and_checksums(tmp_path: Path) -> None:
    source, media = _store_data(tmp_path)
    bundle = create_bundle(source, media, tmp_path / "backups")

    assert not any(path.name.endswith(".tmp") for path in bundle.parent.iterdir())
    assert verify_bundle(bundle) == {"media_files": 2, "referenced_product_images": 1}
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert [entry["path"] for entry in manifest["media"]["files"]] == ["notes.txt", "products/lentil.png"]

    database_target = tmp_path / "restore" / "store.db"
    media_target = tmp_path / "restore" / "media"
    restore_bundle(bundle, database_target, media_target)
    with sqlite3.connect(database_target) as connection:
        assert connection.execute("SELECT amount FROM ledger_entries").fetchone() == (125000,)
    assert (media_target / "products" / "lentil.png").read_bytes() == b"valid-image-bytes"


def test_bundle_round_trip_supports_pre_image_migration_schema(tmp_path: Path) -> None:
    source = tmp_path / "legacy" / "store.db"
    media = tmp_path / "legacy" / "media"
    source.parent.mkdir()
    media.mkdir()
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
        connection.execute("INSERT INTO products (name) VALUES ('legacy lentil')")

    bundle = create_bundle(source, media, tmp_path / "backups")

    assert verify_bundle(bundle) == {"media_files": 0, "referenced_product_images": 0}
    restored_db = tmp_path / "restore" / "store.db"
    restored_media = tmp_path / "restore" / "media"
    restore_bundle(bundle, restored_db, restored_media)
    with sqlite3.connect(restored_db) as connection:
        assert connection.execute("SELECT name FROM products").fetchone() == ("legacy lentil",)


def test_bundle_verification_rejects_missing_or_tampered_manifest(tmp_path: Path) -> None:
    source, media = _store_data(tmp_path)
    first = create_bundle(source, media, tmp_path / "backups")
    (first / "manifest.json.sha256").unlink()
    with pytest.raises(RuntimeError, match="manifest"):
        verify_bundle(first)

    second = create_bundle(source, media, tmp_path / "backups")
    (second / "manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="manifest checksum"):
        verify_bundle(second)


@pytest.mark.parametrize("artifact", ["store.db", "media/products/lentil.png"])
def test_bundle_verification_rejects_tampered_artifacts(tmp_path: Path, artifact: str) -> None:
    source, media = _store_data(tmp_path)
    bundle = create_bundle(source, media, tmp_path / "backups")
    with (bundle / artifact).open("ab") as stream:
        stream.write(b"tampered")

    with pytest.raises(RuntimeError, match="checksum|size"):
        verify_bundle(bundle)


def test_bundle_fails_when_database_references_missing_product_image(tmp_path: Path) -> None:
    source = tmp_path / "store.db"
    media = tmp_path / "media"
    media.mkdir()
    _store_database(source, "missing.png")

    with pytest.raises(RuntimeError, match="missing product images"):
        create_bundle(source, media, tmp_path / "backups")
    assert list((tmp_path / "backups").iterdir()) == []


@pytest.mark.parametrize("destination_kind", ["inside-media", "contains-source"])
def test_bundle_rejects_overlapping_data_and_destination_paths(tmp_path: Path, destination_kind: str) -> None:
    source, media = _store_data(tmp_path)
    destination = media / "backups" if destination_kind == "inside-media" else source.parent

    with pytest.raises(ValueError, match="destination|source"):
        create_bundle(source, media, destination)


def test_bundle_lock_contention_fails_without_publishing_partial_data(tmp_path: Path) -> None:
    source, media = _store_data(tmp_path)
    destination = tmp_path / "backups"

    with exclusive_data_lock(data_lock_path(media)):
        with pytest.raises(TimeoutError, match="data lock"):
            create_bundle(source, media, destination, lock_timeout=0)
    assert list(destination.iterdir()) == []


def test_bundle_copy_failure_removes_staging_and_does_not_publish(tmp_path: Path, monkeypatch) -> None:
    source, media = _store_data(tmp_path)
    destination = tmp_path / "backups"

    def fail_copy(*_args, **_kwargs):
        raise OSError("simulated media failure")

    monkeypatch.setattr(sqlite_backup.shutil, "copy2", fail_copy)
    with pytest.raises(OSError, match="simulated"):
        create_bundle(source, media, destination)
    assert list(destination.iterdir()) == []


def test_restore_bundle_refuses_existing_target(tmp_path: Path) -> None:
    source, media = _store_data(tmp_path)
    bundle = create_bundle(source, media, tmp_path / "backups")
    target = tmp_path / "restore.db"
    target.write_bytes(b"do not replace")

    with pytest.raises(FileExistsError, match="must not already exist"):
        restore_bundle(bundle, target, tmp_path / "restored-media")
    assert target.read_bytes() == b"do not replace"


def test_restore_bundle_rejects_targets_inside_bundle_or_overlapping_each_other(tmp_path: Path) -> None:
    source, media = _store_data(tmp_path)
    bundle = create_bundle(source, media, tmp_path / "backups")

    with pytest.raises(ValueError, match="outside"):
        restore_bundle(bundle, bundle / "restored.db", tmp_path / "restored-media")
    with pytest.raises(ValueError, match="overlap"):
        restore_bundle(bundle, tmp_path / "restore" / "media" / "store.db", tmp_path / "restore" / "media")


def test_bundle_retention_keeps_newest_and_unrelated_paths(tmp_path: Path) -> None:
    source, media = _store_data(tmp_path)
    destination = tmp_path / "backups"
    old = create_bundle(source, media, destination, now=datetime(2026, 1, 1, tzinfo=timezone.utc))
    newest = create_bundle(source, media, destination, now=datetime(2026, 2, 1, tzinfo=timezone.utc))
    unrelated = destination / "customer-files"
    unrelated.mkdir()
    invalid_exact_name = destination / "store-bundle-20250101T000000.000000Z"
    invalid_exact_name.mkdir()
    misleading_prefix = destination / "store-bundle-old-customer-files"
    misleading_prefix.mkdir()
    old_timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp()
    newest_timestamp = datetime(2026, 2, 1, tzinfo=timezone.utc).timestamp()
    os.utime(old, (old_timestamp, old_timestamp))
    os.utime(newest, (newest_timestamp, newest_timestamp))

    removed = prune_bundles(
        destination,
        7,
        keep_last=1,
        now=datetime(2026, 2, 20, tzinfo=timezone.utc),
    )

    assert removed == [old]
    assert newest.is_dir()
    assert unrelated.is_dir()
    assert invalid_exact_name.is_dir()
    assert misleading_prefix.is_dir()
