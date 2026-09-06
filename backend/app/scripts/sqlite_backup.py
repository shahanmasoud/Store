"""Safe, dependency-free backup and verification utilities for SQLite.

The default backup directory is deliberately outside the source repository.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote


BACKUP_PREFIX = "store-"
BACKUP_SUFFIX = ".db"


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
    if final_path.exists() or temp_path.exists():
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
        os.replace(temp_path, final_path)
        checksum = sha256_file(final_path)
        checksum_path = final_path.with_suffix(final_path.suffix + ".sha256")
        checksum_path.write_text(f"{checksum}  {final_path.name}\n", encoding="ascii")
        _restrict_permissions(final_path, 0o600)
        _restrict_permissions(checksum_path, 0o600)
        return final_path
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def verify_backup(path: Path) -> str:
    path = path.expanduser().resolve()
    integrity_check(path)
    actual = sha256_file(path)
    checksum_path = path.with_suffix(path.suffix + ".sha256")
    if checksum_path.exists():
        expected = checksum_path.read_text(encoding="ascii").split()[0]
        if actual != expected:
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


def _default_source() -> Path:
    from app.core.config import get_settings

    return sqlite_path_from_url(get_settings().database_url)


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
        else:
            print(f"Backup restored and verified: {restore_backup(args.backup, args.target, replace=args.replace)}")
        return 0
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
        print(f"Backup operation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
