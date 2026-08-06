"""Durable atomic file replacement helpers."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def atomic_write_bytes(
    path: Path, payload: bytes, *, mode: int | None = None
) -> None:
    """Write *payload* durably and atomically replace *path*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
            temporary = Path(stream.name)
        if mode is not None:
            temporary.chmod(mode)
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def atomic_write_text(
    path: Path, text: str, *, mode: int | None = None
) -> None:
    """Encode UTF-8 text and atomically replace *path*."""
    atomic_write_bytes(path, text.encode("utf-8"), mode=mode)
