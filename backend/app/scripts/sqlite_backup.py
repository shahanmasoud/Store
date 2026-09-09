"""Safe, dependency-free backup and verification utilities for SQLite.

The default backup directory is deliberately outside the source repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote

from app.services.data_lock import data_lock_path, exclusive_data_lock


BACKUP_PREFIX = "store-"
BACKUP_SUFFIX = ".db"
BUNDLE_PREFIX = "store-bundle-"
BUNDLE_SCHEMA_VERSION = 1
BUNDLE_NAME_PATTERN = re.compile(r"^store-bundle-\d{8}T\d{6}\.\d{6}Z$")


def _paths_overlap(first: Path, second: Path) -> bool:
    first = first.resolve()
    second = second.resolve()
    return first == second or first in second.parents or second in first.parents


def sqlite_path_from_url(database_url: str) -> Path:
    """Return the filesystem path from a SQLite SQLAlchemy URL."""
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError("Only file-based SQLite DATABASE_URL values are supported")
    raw_path = unquote(database_url[len(prefix) :])
    if not raw_path or raw_path == ":memory:":
        raise ValueError("An on-disk SQLite database is required")
    # Four slashes represent an absolute POSIX path; Windows drive paths are
    # already returned as C:/... after removing sqlite:///.
    if raw_path.startswith("/"):
        return Path(raw_path)
    return Path(raw_path).resolve()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def integrity_check(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        rows = connection.execute("PRAGMA integrity_check").fetchall()
    finally:
        connection.close()
    messages = [str(row[0]) for row in rows]
    if messages != ["ok"]:
        raise RuntimeError(f"SQLite integrity check failed: {messages}")


def _restrict_permissions(path: Path, mode: int) -> None:
    try:
        path.chmod(mode)
    except OSError:
        # Windows ACLs and some hosted filesystems do not implement POSIX mode
        # bits. The containing user-private directory remains the main guard.
        pass


def create_backup(source: Path, destination_dir: Path, *, now: datetime | None = None) -> Path:
    source = source.expanduser().resolve()
    destination_dir = destination_dir.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    destination_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    _restrict_permissions(destination_dir, 0o700)

    timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    stamp = timestamp.strftime("%Y%m%dT%H%M%S.%fZ")
    final_path = destination_dir / f"{BACKUP_PREFIX}{stamp}{BACKUP_SUFFIX}"
    temp_path = destination_dir / f".{final_path.name}.{os.getpid()}.tmp"
    checksum_path = final_path.with_suffix(final_path.suffix + ".sha256")
    checksum_temp = destination_dir / f".{checksum_path.name}.{os.getpid()}.tmp"
    if final_path.exists() or temp_path.exists() or checksum_path.exists() or checksum_temp.exists():
        raise FileExistsError(final_path)

    try:
        source_db = sqlite3.connect(source)
        backup_db = sqlite3.connect(temp_path)
        try:
            source_db.backup(backup_db)
        finally:
            backup_db.close()
            source_db.close()
        integrity_check(temp_path)
        _restrict_permissions(temp_path, 0o600)
        checksum = sha256_file(temp_path)
        checksum_temp.write_text(f"{checksum}  {final_path.name}\n", encoding="ascii")
        _restrict_permissions(checksum_temp, 0o600)
        os.replace(temp_path, final_path)
        os.replace(checksum_temp, checksum_path)
        _restrict_permissions(final_path, 0o600)
        _restrict_permissions(checksum_path, 0o600)
        return final_path
    except Exception:
        temp_path.unlink(missing_ok=True)
        checksum_temp.unlink(missing_ok=True)
        final_path.unlink(missing_ok=True)
        checksum_path.unlink(missing_ok=True)
        raise


def verify_backup(path: Path) -> str:
    path = path.expanduser().resolve()
    integrity_check(path)
    actual = sha256_file(path)
    checksum_path = path.with_suffix(path.suffix + ".sha256")
    if not checksum_path.is_file():
        raise RuntimeError("SHA-256 checksum is missing")
    checksum_parts = checksum_path.read_text(encoding="ascii").split()
    if len(checksum_parts) != 2 or checksum_parts[1] != path.name:
        raise RuntimeError("SHA-256 checksum format is invalid")
    if actual != checksum_parts[0]:
        raise RuntimeError("SHA-256 checksum does not match")
    return actual


def restore_backup(backup: Path, target: Path, *, replace: bool = False) -> Path:
    backup = backup.expanduser().resolve()
    target = target.expanduser().resolve()
    verify_backup(backup)
    if target.exists() and not replace:
        raise FileExistsError(f"Restore target exists; pass --replace explicitly: {target}")
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temp_path = target.parent / f".{target.name}.{os.getpid()}.restore.tmp"
    try:
        backup_db = sqlite3.connect(backup)
        target_db = sqlite3.connect(temp_path)
        try:
            backup_db.backup(target_db)
        finally:
            target_db.close()
            backup_db.close()
        integrity_check(temp_path)
        _restrict_permissions(temp_path, 0o600)
        os.replace(temp_path, target)
        _restrict_permissions(target, 0o600)
        return target
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def prune_backups(destination_dir: Path, keep_days: int, *, now: datetime | None = None) -> list[Path]:
    if keep_days < 1:
        raise ValueError("keep_days must be at least 1")
    destination_dir = destination_dir.expanduser().resolve()
    if not destination_dir.is_dir():
        return []
    cutoff = (now or datetime.now(timezone.utc)).timestamp() - timedelta(days=keep_days).total_seconds()
    removed: list[Path] = []
    for path in destination_dir.glob(f"{BACKUP_PREFIX}*{BACKUP_SUFFIX}"):
        if path.is_file() and path.stat().st_mtime < cutoff:
            checksum_path = path.with_suffix(path.suffix + ".sha256")
            path.unlink()
            checksum_path.unlink(missing_ok=True)
            removed.append(path)
    return removed


def _safe_media_files(media_root: Path) -> list[Path]:
    if not media_root.exists():
        return []
    if not media_root.is_dir() or media_root.is_symlink():
        raise ValueError("MEDIA_ROOT must be a real directory")
    files: list[Path] = []
    for path in media_root.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"Symbolic links are not allowed in media backups: {path}")
        if path.is_file():
            files.append(path)
    return sorted(files, key=lambda item: item.relative_to(media_root).as_posix())


def _manifest_payload(bundle: Path, created_at: datetime) -> dict[str, object]:
    database = bundle / "store.db"
    media_dir = bundle / "media"
    media_files = []
    if media_dir.is_dir():
        for path in _safe_media_files(media_dir):
            media_files.append(
                {
                    "path": path.relative_to(media_dir).as_posix(),
                    "size": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    return {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "created_at_utc": created_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "database": {"path": "store.db", "size": database.stat().st_size, "sha256": sha256_file(database)},
        "media": {"path": "media", "files": media_files},
    }


def create_bundle(
    source: Path,
    media_root: Path,
    destination_dir: Path,
    *,
    now: datetime | None = None,
    lock_timeout: float = 10.0,
) -> Path:
    """Atomically publish a verified SQLite + media backup directory."""
    source = source.expanduser().resolve()
    media_root = media_root.expanduser().resolve()
    destination_dir = destination_dir.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if _paths_overlap(media_root, destination_dir):
        raise ValueError("Backup destination must not overlap MEDIA_ROOT")
    if destination_dir == source.parent or destination_dir in source.parents:
        raise ValueError("SQLite source must not be inside the backup destination")
    destination_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    _restrict_permissions(destination_dir, 0o700)
    timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    stamp = timestamp.strftime("%Y%m%dT%H%M%S.%fZ")
    final_path = destination_dir / f"{BUNDLE_PREFIX}{stamp}"
    staging = destination_dir / f".{final_path.name}.{os.getpid()}.tmp"
    if final_path.exists() or staging.exists():
        raise FileExistsError(final_path)

    try:
        with exclusive_data_lock(data_lock_path(media_root), timeout=lock_timeout):
            staging.mkdir(mode=0o700)
            database = staging / "store.db"
            source_db = sqlite3.connect(source)
            backup_db = sqlite3.connect(database)
            try:
                source_db.backup(backup_db)
            finally:
                backup_db.close()
                source_db.close()
            integrity_check(database)
            _restrict_permissions(database, 0o600)
            database_checksum = staging / "store.db.sha256"
            database_checksum.write_text(f"{sha256_file(database)}  store.db\n", encoding="ascii")
            _restrict_permissions(database_checksum, 0o600)

            media_destination = staging / "media"
            media_destination.mkdir(mode=0o700)
            for media_file in _safe_media_files(media_root):
                relative = media_file.relative_to(media_root)
                target = media_destination / relative
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                shutil.copy2(media_file, target, follow_symlinks=False)
                _restrict_permissions(target, 0o600)

            manifest = staging / "manifest.json"
            manifest.write_text(
                json.dumps(_manifest_payload(staging, timestamp), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            _restrict_permissions(manifest, 0o600)
            manifest_checksum = staging / "manifest.json.sha256"
            manifest_checksum.write_text(f"{sha256_file(manifest)}  manifest.json\n", encoding="ascii")
            _restrict_permissions(manifest_checksum, 0o600)
            verify_bundle(staging)
            os.replace(staging, final_path)
        return final_path
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def _read_manifest(bundle: Path) -> dict[str, object]:
    manifest_path = bundle / "manifest.json"
    checksum_path = bundle / "manifest.json.sha256"
    if not manifest_path.is_file() or not checksum_path.is_file():
        raise RuntimeError("Bundle manifest or its checksum is missing")
    checksum_parts = checksum_path.read_text(encoding="ascii").split()
    if len(checksum_parts) != 2 or checksum_parts[1] != "manifest.json":
        raise RuntimeError("Bundle manifest checksum format is invalid")
    if sha256_file(manifest_path) != checksum_parts[0]:
        raise RuntimeError("Bundle manifest checksum does not match")
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError("Bundle manifest is invalid") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != BUNDLE_SCHEMA_VERSION:
        raise RuntimeError("Unsupported bundle manifest schema")
    return payload


def verify_bundle(bundle: Path) -> dict[str, int]:
    bundle = bundle.expanduser().resolve()
    if not bundle.is_dir() or bundle.is_symlink():
        raise FileNotFoundError(bundle)
    payload = _read_manifest(bundle)
    database_info = payload.get("database")
    media_info = payload.get("media")
    if not isinstance(database_info, dict) or database_info.get("path") != "store.db":
        raise RuntimeError("Bundle database manifest is invalid")
    database = bundle / "store.db"
    if not database.is_file() or database.is_symlink():
        raise RuntimeError("Bundle database is missing or unsafe")
    if database.stat().st_size != database_info.get("size") or sha256_file(database) != database_info.get("sha256"):
        raise RuntimeError("Bundle database checksum or size does not match")
    verify_backup(database)

    if not isinstance(media_info, dict) or media_info.get("path") != "media" or not isinstance(media_info.get("files"), list):
        raise RuntimeError("Bundle media manifest is invalid")
    media_dir = bundle / "media"
    if not media_dir.is_dir() or media_dir.is_symlink():
        raise RuntimeError("Bundle media directory is missing or unsafe")
    expected: set[str] = set()
    for entry in media_info["files"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise RuntimeError("Bundle media entry is invalid")
        relative = Path(entry["path"])
        if relative.is_absolute() or ".." in relative.parts or relative.as_posix() in expected:
            raise RuntimeError("Bundle media path is unsafe or duplicated")
        expected.add(relative.as_posix())
        media_file = (media_dir / relative).resolve()
        if media_dir not in media_file.parents or not media_file.is_file() or media_file.is_symlink():
            raise RuntimeError(f"Bundle media file is missing or unsafe: {relative.as_posix()}")
        if media_file.stat().st_size != entry.get("size") or sha256_file(media_file) != entry.get("sha256"):
            raise RuntimeError(f"Bundle media checksum or size does not match: {relative.as_posix()}")
    actual = {path.relative_to(media_dir).as_posix() for path in _safe_media_files(media_dir)}
    if actual != expected:
        raise RuntimeError("Bundle media files do not exactly match the manifest")

    with closing(sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)) as connection:
        has_products = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='products'"
        ).fetchone()
        referenced = set()
        if has_products:
            referenced = {
                f"products/{row[0]}"
                for row in connection.execute("SELECT image_filename FROM products WHERE image_filename IS NOT NULL")
            }
    missing = referenced - actual
    if missing:
        raise RuntimeError(f"Bundle is missing product images referenced by SQLite: {sorted(missing)}")
    return {"media_files": len(actual), "referenced_product_images": len(referenced)}


def restore_bundle(bundle: Path, database_target: Path, media_target: Path) -> tuple[Path, Path]:
    """Restore a verified bundle only into two new targets."""
    bundle = bundle.expanduser().resolve()
    database_target = database_target.expanduser().resolve()
    media_target = media_target.expanduser().resolve()
    verify_bundle(bundle)
    if bundle == database_target or bundle in database_target.parents or bundle == media_target or bundle in media_target.parents:
        raise ValueError("Bundle restore targets must be outside the source bundle")
    if _paths_overlap(database_target, media_target):
        raise ValueError("Database and media restore targets must not overlap")
    if database_target.exists() or media_target.exists():
        raise FileExistsError("Bundle restore targets must not already exist")
    database_target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    media_target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    database_temp = database_target.parent / f".{database_target.name}.{os.getpid()}.restore.tmp"
    media_temp = media_target.parent / f".{media_target.name}.{os.getpid()}.restore.tmp"
    try:
        restore_backup(bundle / "store.db", database_temp)
        shutil.copytree(bundle / "media", media_temp, symlinks=False)
        verify_bundle_contents(database_temp, media_temp)
        os.replace(database_temp, database_target)
        try:
            os.replace(media_temp, media_target)
        except Exception:
            database_target.unlink(missing_ok=True)
            raise
        return database_target, media_target
    except Exception:
        database_temp.unlink(missing_ok=True)
        if media_temp.exists():
            shutil.rmtree(media_temp)
        raise


def verify_bundle_contents(database: Path, media_root: Path) -> None:
    integrity_check(database)
    with closing(sqlite3.connect(f"file:{database.resolve().as_posix()}?mode=ro", uri=True)) as connection:
        has_products = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='products'"
        ).fetchone()
        if not has_products:
            return
        filenames = [row[0] for row in connection.execute("SELECT image_filename FROM products WHERE image_filename IS NOT NULL")]
    for filename in filenames:
        path = (media_root.resolve() / "products" / filename).resolve()
        if media_root.resolve() not in path.parents or not path.is_file():
            raise RuntimeError(f"Restored product image is missing: {filename}")


def prune_bundles(destination_dir: Path, keep_days: int, *, keep_last: int = 1, now: datetime | None = None) -> list[Path]:
    if keep_days < 1 or keep_last < 1:
        raise ValueError("keep_days and keep_last must be at least 1")
    destination_dir = destination_dir.expanduser().resolve()
    if not destination_dir.is_dir():
        return []
    bundles: list[tuple[datetime, Path]] = []
    for path in destination_dir.iterdir():
        if not path.is_dir() or path.is_symlink() or BUNDLE_NAME_PATTERN.fullmatch(path.name) is None:
            continue
        try:
            verify_bundle(path)
            payload = _read_manifest(path)
            created_raw = payload.get("created_at_utc")
            if not isinstance(created_raw, str) or not created_raw.endswith("Z"):
                continue
            created_at = datetime.fromisoformat(created_raw.removesuffix("Z") + "+00:00")
            if created_at.tzinfo is None:
                continue
        except (OSError, ValueError, RuntimeError):
            continue
        bundles.append((created_at.astimezone(timezone.utc), path))
    bundles.sort(key=lambda item: item[0], reverse=True)
    cutoff = (now or datetime.now(timezone.utc)).timestamp() - timedelta(days=keep_days).total_seconds()
    removed: list[Path] = []
    for created_at, path in bundles[keep_last:]:
        if created_at.timestamp() < cutoff:
            shutil.rmtree(path)
            removed.append(path)
    return removed


def _default_source() -> Path:
    from app.core.config import get_settings

    return sqlite_path_from_url(get_settings().database_url)


def _default_media_root() -> Path:
    from app.core.config import get_settings

    return get_settings().media_root


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Back up and verify the Store SQLite database")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup = subparsers.add_parser("backup", help="Create and verify a consistent SQLite backup")
    backup.add_argument("--source", type=Path, help="DB path; defaults to DATABASE_URL")
    backup.add_argument("--destination", type=Path, default=Path.home() / "store-backups")
    backup.add_argument("--keep-days", type=int, help="Optionally delete matching backups older than N days")

    verify = subparsers.add_parser("verify", help="Run integrity and optional checksum verification")
    verify.add_argument("backup", type=Path)

    restore = subparsers.add_parser("restore", help="Restore to a target path after verification")
    restore.add_argument("backup", type=Path)
    restore.add_argument("target", type=Path)
    restore.add_argument("--replace", action="store_true", help="Explicitly allow replacement of target")

    bundle = subparsers.add_parser("bundle", help="Create and verify an atomic SQLite + media bundle")
    bundle.add_argument("--source", type=Path, help="DB path; defaults to DATABASE_URL")
    bundle.add_argument("--media-root", type=Path, help="Media path; defaults to MEDIA_ROOT")
    bundle.add_argument("--destination", type=Path, default=Path.home() / "store-backups")
    bundle.add_argument("--keep-days", type=int)
    bundle.add_argument("--keep-last", type=int, default=1)
    bundle.add_argument("--lock-timeout", type=float, default=10.0)

    verify_bundle_parser = subparsers.add_parser("verify-bundle", help="Verify a DB + media bundle")
    verify_bundle_parser.add_argument("bundle", type=Path)

    restore_bundle_parser = subparsers.add_parser("restore-bundle", help="Restore a bundle into new targets")
    restore_bundle_parser.add_argument("bundle", type=Path)
    restore_bundle_parser.add_argument("database_target", type=Path)
    restore_bundle_parser.add_argument("media_target", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "backup":
            source = args.source or _default_source()
            result = create_backup(source, args.destination)
            if args.keep_days is not None:
                prune_backups(args.destination, args.keep_days)
            print(f"Backup created and verified: {result}")
        elif args.command == "verify":
            print(f"Backup verified; SHA-256: {verify_backup(args.backup)}")
        elif args.command == "restore":
            print(f"Backup restored and verified: {restore_backup(args.backup, args.target, replace=args.replace)}")
        elif args.command == "bundle":
            result = create_bundle(
                args.source or _default_source(),
                args.media_root or _default_media_root(),
                args.destination,
                lock_timeout=args.lock_timeout,
            )
            if args.keep_days is not None:
                prune_bundles(args.destination, args.keep_days, keep_last=args.keep_last)
            print(f"Backup bundle created and verified: {result}")
        elif args.command == "verify-bundle":
            print(f"Backup bundle verified: {verify_bundle(args.bundle)}")
        else:
            database, media = restore_bundle(args.bundle, args.database_target, args.media_target)
            print(f"Backup bundle restored and verified: database={database}, media={media}")
        return 0
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
        print(f"Backup operation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
