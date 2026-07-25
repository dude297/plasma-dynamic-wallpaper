"""HEIC frame extraction and cache management."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


class CacheError(RuntimeError):
    """Raised when cached wallpaper frames cannot be prepared."""


def _frame_sort_key(path: Path) -> tuple[int, str]:
    digits = "".join(
        character for character in path.stem if character.isdigit()
    )

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


def _write_source_marker(
    cache_dir: Path,
    heic_file: Path,
    frame_count: int,
) -> None:
    _source_marker(cache_dir).write_text(
        f"{_source_timestamp(heic_file)}\n{frame_count}\n",
        encoding="utf-8",
    )


def cache_is_current(heic_file: Path, cache_dir: Path) -> bool:
    marker = _source_marker(cache_dir)

    if not marker.is_file():
        return False

    frames = find_frames(cache_dir)
    if not frames:
        return False

    try:
        marker_lines = marker.read_text(encoding="utf-8").splitlines()
        recorded_timestamp, recorded_count = marker_lines
        expected_count = int(recorded_count)
    except (OSError, TypeError, ValueError):
        return False

    return recorded_timestamp == _source_timestamp(
        heic_file
    ) and expected_count == len(frames)


def extract_frames(heic_file: Path, cache_dir: Path) -> list[Path]:
    cache_parent = cache_dir.parent
    cache_parent.mkdir(parents=True, exist_ok=True)

    staging_dir = Path(
        tempfile.mkdtemp(
            prefix=f".{cache_dir.name}.rebuild-",
            dir=cache_parent,
        )
    )
    backup_dir = cache_parent / f".{cache_dir.name}.backup"
    output_path = staging_dir / "frame.png"

    try:
        try:
            subprocess.run(
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

        frames = find_frames(staging_dir)

        if not frames:
            raise CacheError(f"No frames were extracted into {cache_dir}")

        _write_source_marker(
            staging_dir,
            heic_file,
            len(frames),
        )

        if backup_dir.exists():
            shutil.rmtree(backup_dir)

        if cache_dir.exists():
            cache_dir.rename(backup_dir)

        try:
            staging_dir.rename(cache_dir)
        except BaseException:
            if backup_dir.exists() and not cache_dir.exists():
                backup_dir.rename(cache_dir)
            raise

        if backup_dir.exists():
            shutil.rmtree(backup_dir)

        return find_frames(cache_dir)
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)


def prepare_frames(
    heic_file: Path,
    cache_dir: Path,
) -> list[Path]:
    if cache_is_current(heic_file, cache_dir):
        return find_frames(cache_dir)

    return extract_frames(heic_file, cache_dir)
