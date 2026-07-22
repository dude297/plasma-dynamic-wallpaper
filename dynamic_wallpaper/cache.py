"""HEIC frame extraction and cache management."""

from __future__ import annotations

import subprocess
from pathlib import Path


class CacheError(RuntimeError):
    """Raised when cached wallpaper frames cannot be prepared."""


def _frame_sort_key(path: Path) -> tuple[int, str]:
    digits = "".join(character for character in path.stem if character.isdigit())

    if digits:
        return int(digits), path.name

    return 0, path.name


def find_frames(cache_dir: Path) -> list[Path]:
    return sorted(
        cache_dir.glob("*.png"),
        key=_frame_sort_key,
    )


def _source_marker(cache_dir: Path) -> Path:
    return cache_dir / ".source-mtime"


def _source_timestamp(heic_file: Path) -> str:
    return str(heic_file.stat().st_mtime_ns)


def cache_is_current(heic_file: Path, cache_dir: Path) -> bool:
    marker = _source_marker(cache_dir)

    if not marker.is_file():
        return False

    if not find_frames(cache_dir):
        return False

    try:
        recorded_timestamp = marker.read_text(
            encoding="utf-8"
        ).strip()
    except OSError:
        return False

    return recorded_timestamp == _source_timestamp(heic_file)


def extract_frames(heic_file: Path, cache_dir: Path) -> list[Path]:
    cache_dir.mkdir(parents=True, exist_ok=True)

    for existing_frame in cache_dir.glob("*.png"):
        existing_frame.unlink()

    output_path = cache_dir / "frame.png"

    try:
        result = subprocess.run(
            [
                "heif-convert",
                str(heic_file),
                str(output_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise CacheError(
            "heif-convert is required but was not found"
        ) from exc
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or "heif-convert failed"
        raise CacheError(message) from exc

    frames = find_frames(cache_dir)

    if not frames:
        raise CacheError(
            f"No frames were extracted into {cache_dir}"
        )

    _source_marker(cache_dir).write_text(
        _source_timestamp(heic_file),
        encoding="utf-8",
    )

    return frames


def prepare_frames(
    heic_file: Path,
    cache_dir: Path,
) -> list[Path]:
    if cache_is_current(heic_file, cache_dir):
        return find_frames(cache_dir)

    return extract_frames(heic_file, cache_dir)
