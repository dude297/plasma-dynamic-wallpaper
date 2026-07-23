"""Tests for HEIC frame extraction and cache management."""

from pathlib import Path
import subprocess

import pytest

from dynamic_wallpaper.cache import (
    CacheError,
    cache_is_current,
    extract_frames,
    find_frames,
    prepare_frames,
)


def test_find_frames_sorts_numeric_frame_names(tmp_path: Path) -> None:
    for name in ("frame-10.png", "frame-2.png", "cover.png", "frame-1.png"):
        (tmp_path / name).touch()

    assert [path.name for path in find_frames(tmp_path)] == [
        "cover.png",
        "frame-1.png",
        "frame-2.png",
        "frame-10.png",
    ]


def test_cache_is_current_requires_marker_and_frames(tmp_path: Path) -> None:
    heic_file = tmp_path / "wallpaper.heic"
    cache_dir = tmp_path / "cache"
    heic_file.touch()
    cache_dir.mkdir()

    assert cache_is_current(heic_file, cache_dir) is False

    (cache_dir / ".source-mtime").write_text(
        str(heic_file.stat().st_mtime_ns),
        encoding="utf-8",
    )

    assert cache_is_current(heic_file, cache_dir) is False


def test_cache_is_current_matches_source_timestamp(tmp_path: Path) -> None:
    heic_file = tmp_path / "wallpaper.heic"
    cache_dir = tmp_path / "cache"
    heic_file.touch()
    cache_dir.mkdir()
    (cache_dir / "frame-1.png").touch()
    (cache_dir / ".source-mtime").write_text(
        str(heic_file.stat().st_mtime_ns),
        encoding="utf-8",
    )

    assert cache_is_current(heic_file, cache_dir) is True


def test_cache_is_current_rejects_stale_timestamp(tmp_path: Path) -> None:
    heic_file = tmp_path / "wallpaper.heic"
    cache_dir = tmp_path / "cache"
    heic_file.touch()
    cache_dir.mkdir()
    (cache_dir / "frame-1.png").touch()
    (cache_dir / ".source-mtime").write_text("0", encoding="utf-8")

    assert cache_is_current(heic_file, cache_dir) is False


def test_extract_frames_removes_old_frames_and_records_source(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    heic_file = tmp_path / "wallpaper.heic"
    cache_dir = tmp_path / "cache"
    heic_file.touch()
    cache_dir.mkdir()
    old_frame = cache_dir / "old-99.png"
    old_frame.touch()

    def fake_run(command: list[str], **kwargs: object) -> None:
        assert command == [
            "heif-convert",
            str(heic_file),
            str(cache_dir / "frame.png"),
        ]
        assert kwargs == {
            "check": True,
            "capture_output": True,
            "text": True,
        }
        (cache_dir / "frame-1.png").touch()
        (cache_dir / "frame-2.png").touch()

    monkeypatch.setattr(subprocess, "run", fake_run)

    frames = extract_frames(heic_file, cache_dir)

    assert old_frame.exists() is False
    assert [path.name for path in frames] == ["frame-1.png", "frame-2.png"]
    assert (cache_dir / ".source-mtime").read_text(encoding="utf-8") == str(
        heic_file.stat().st_mtime_ns
    )


def test_extract_frames_reports_missing_converter(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    heic_file = tmp_path / "wallpaper.heic"

    def missing_converter(*args: object, **kwargs: object) -> None:
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", missing_converter)

    with pytest.raises(CacheError, match="heif-convert is required"):
        extract_frames(heic_file, tmp_path / "cache")


def test_extract_frames_reports_converter_stderr(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    error = subprocess.CalledProcessError(
        1,
        ["heif-convert"],
        stderr="decoder failed\n",
    )

    def failed_converter(*args: object, **kwargs: object) -> None:
        raise error

    monkeypatch.setattr(subprocess, "run", failed_converter)

    with pytest.raises(CacheError, match="decoder failed"):
        extract_frames(tmp_path / "wallpaper.heic", tmp_path / "cache")


def test_extract_frames_rejects_empty_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: None)

    with pytest.raises(CacheError, match="No frames were extracted"):
        extract_frames(tmp_path / "wallpaper.heic", tmp_path / "cache")


def test_prepare_frames_reuses_current_cache(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    heic_file = tmp_path / "wallpaper.heic"
    cache_dir = tmp_path / "cache"
    heic_file.touch()
    cache_dir.mkdir()
    frame = cache_dir / "frame-1.png"
    frame.touch()
    (cache_dir / ".source-mtime").write_text(
        str(heic_file.stat().st_mtime_ns),
        encoding="utf-8",
    )

    def should_not_run(*args: object, **kwargs: object) -> None:
        raise AssertionError("converter should not be called")

    monkeypatch.setattr(subprocess, "run", should_not_run)

    assert prepare_frames(heic_file, cache_dir) == [frame]


def test_prepare_frames_extracts_when_cache_is_stale(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    heic_file = tmp_path / "wallpaper.heic"
    cache_dir = tmp_path / "cache"
    heic_file.touch()

    def fake_run(*args: object, **kwargs: object) -> None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "frame-1.png").touch()

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert prepare_frames(heic_file, cache_dir) == [
        cache_dir / "frame-1.png"
    ]
