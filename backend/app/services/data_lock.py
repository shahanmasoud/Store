"""Cross-process advisory lock shared by backups and media mutations."""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def data_lock_path(media_root: Path) -> Path:
    """Keep the shared lock beside the configured media directory."""
    return media_root.expanduser().resolve().parent / ".store-data.lock"


def _try_lock(stream) -> bool:
    if os.name == "nt":
        import msvcrt

        stream.seek(0)
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False

    import fcntl

    try:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except BlockingIOError:
        return False


def _unlock(stream) -> None:
    if os.name == "nt":
        import msvcrt

        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        return

    import fcntl

    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


@contextmanager
def exclusive_data_lock(path: Path, *, timeout: float = 10.0, poll_interval: float = 0.05) -> Iterator[None]:
    """Acquire a portable advisory file lock or fail after ``timeout`` seconds."""
    if timeout < 0:
        raise ValueError("lock timeout cannot be negative")
    path = path.expanduser().resolve()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    stream = path.open("a+b")
    try:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        deadline = time.monotonic() + timeout
        while not _try_lock(stream):
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out waiting for data lock: {path}")
            time.sleep(min(poll_interval, max(0.0, deadline - time.monotonic())))
        try:
            yield
        finally:
            _unlock(stream)
    finally:
        stream.close()
