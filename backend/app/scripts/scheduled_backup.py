"""Monitor-friendly wrapper for scheduled Store backup bundles.

This command intentionally requires explicit output paths. It never emits
exception messages because those may contain configured paths or credentials.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.scripts.sqlite_backup import (
    _default_media_root,
    _default_source,
    _paths_overlap,
    _restrict_permissions,
    create_bundle,
    prune_bundles,
    verify_bundle,
)


def _utc_text(value: datetime | None = None) -> str:
    return (value or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_paths(source: Path, media_root: Path, destination: Path, status_file: Path) -> tuple[Path, Path, Path, Path]:
    if status_file.is_symlink():
        raise ValueError("status file must not be a symbolic link")
    source = source.expanduser().resolve()
    media_root = media_root.expanduser().resolve()
    destination = destination.expanduser().resolve()
    status_file = status_file.expanduser().resolve()
    if status_file.suffix.lower() != ".json":
        raise ValueError("status file must use a .json suffix")
    if status_file.exists() and not status_file.is_file():
        raise ValueError("status file must be a regular file")
    if status_file == source or _paths_overlap(status_file, media_root):
        raise ValueError("status file must be separate from operational data")
    if status_file == destination:
        raise ValueError("status file must not be the destination directory")
    return source, media_root, destination, status_file


def write_status_atomic(status_file: Path, payload: dict[str, object]) -> None:
    status_file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    _restrict_permissions(status_file.parent, 0o700)
    temporary = status_file.parent / f".{status_file.name}.{os.getpid()}.tmp"
    if temporary.exists():
        temporary.unlink()
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        _restrict_permissions(temporary, 0o600)
        os.replace(temporary, status_file)
        _restrict_permissions(status_file, 0o600)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def run_scheduled_backup(
    *,
    source: Path | None,
    media_root: Path | None,
    destination: Path,
    status_file: Path,
    keep_days: int,
    keep_last: int,
    lock_timeout: float = 10.0,
) -> int:
    started_at = _utc_text()
    try:
        if keep_days < 1:
            raise ValueError("keep_days must be at least 1")
        if keep_last < 1:
            raise ValueError("keep_last must be at least 1")
        if lock_timeout <= 0:
            raise ValueError("lock_timeout must be positive")
        source = source or _default_source()
        media_root = media_root or _default_media_root()
        source, media_root, destination, status_file = _safe_paths(
            source, media_root, destination, status_file
        )
        write_status_atomic(
            status_file,
            {"schema_version": 1, "state": "running", "started_at_utc": started_at},
        )
        bundle = create_bundle(
            source,
            media_root,
            destination,
            lock_timeout=lock_timeout,
        )
        verification = verify_bundle(bundle)
        removed = prune_bundles(destination, keep_days, keep_last=keep_last)
        write_status_atomic(
            status_file,
            {
                "schema_version": 1,
                "state": "success",
                "started_at_utc": started_at,
                "finished_at_utc": _utc_text(),
                "bundle_name": bundle.name,
                "media_files": verification["media_files"],
                "referenced_product_images": verification["referenced_product_images"],
                "pruned_bundle_names": [path.name for path in removed],
            },
        )
        print("Scheduled backup completed successfully")
        return 0
    except Exception as exc:
        # Only the exception class is safe for monitoring. Exception text can
        # contain private paths, URLs, or values supplied by hosting settings.
        failure = {
            "schema_version": 1,
            "state": "failure",
            "started_at_utc": started_at,
            "finished_at_utc": _utc_text(),
            "error_code": type(exc).__name__,
        }
        try:
            safe_status = status_file.expanduser().resolve()
            if not status_file.is_symlink() and safe_status.suffix.lower() == ".json":
                write_status_atomic(safe_status, failure)
        except Exception:
            pass
        print(f"Scheduled backup failed ({type(exc).__name__})", file=sys.stderr)
        return 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run and monitor a scheduled Store backup bundle")
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--status-file", type=Path, required=True)
    parser.add_argument("--source", type=Path, help="DB path; defaults to DATABASE_URL")
    parser.add_argument("--media-root", type=Path, help="Media path; defaults to MEDIA_ROOT")
    parser.add_argument("--keep-days", type=int, default=30)
    parser.add_argument("--keep-last", type=int, default=7)
    parser.add_argument("--lock-timeout", type=float, default=10.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return run_scheduled_backup(
        source=args.source,
        media_root=args.media_root,
        destination=args.destination,
        status_file=args.status_file,
        keep_days=args.keep_days,
        keep_last=args.keep_last,
        lock_timeout=args.lock_timeout,
    )


if __name__ == "__main__":
    raise SystemExit(main())
