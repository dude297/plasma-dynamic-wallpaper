"""Tests for persisted wallpaper state."""

import json
from pathlib import Path

import pytest

from dynamic_wallpaper.state import (
    StateError,
    is_current,
    load_state,
    save_state,
)


def test_load_state_returns_empty_for_missing_file(tmp_path: Path) -> None:
    assert load_state(tmp_path / "state.json") == {}


@pytest.mark.parametrize("contents", ["not json", "[]", '"wallpaper"'])
def test_load_state_returns_empty_for_invalid_state(
    tmp_path: Path,
    contents: str,
) -> None:
    state_file = tmp_path / "state.json"
    state_file.write_text(contents, encoding="utf-8")

    assert load_state(state_file) == {}


def test_load_state_returns_dictionary(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    expected = {"wallpaper": "/tmp/frame.png", "frame_index": 3}
    state_file.write_text(json.dumps(expected), encoding="utf-8")

    assert load_state(state_file) == expected


def test_is_current_compares_resolved_paths(tmp_path: Path) -> None:
    wallpaper = tmp_path / "frames" / "frame.png"
    wallpaper.parent.mkdir()
    wallpaper.touch()
    state_file = tmp_path / "state.json"
    state_file.write_text(
        json.dumps(
            {
                "wallpaper": str(
                    wallpaper.parent / ".." / "frames" / "frame.png"
                )
            }
        ),
        encoding="utf-8",
    )

    assert is_current(state_file, wallpaper) is True


def test_is_current_rejects_missing_wallpaper_value(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    state_file.write_text('{"frame_index": 1}', encoding="utf-8")

    assert is_current(state_file, tmp_path / "frame.png") is False


def test_save_state_creates_parent_and_atomically_replaces_file(
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "nested" / "state.json"
    wallpaper = tmp_path / "frame.png"
    wallpaper.touch()

    save_state(state_file, wallpaper, 4)

    saved = json.loads(state_file.read_text(encoding="utf-8"))
    assert saved["wallpaper"] == str(wallpaper.resolve())
    assert saved["frame_index"] == 4
    assert saved["applied_at"].endswith("+00:00")
    assert state_file.read_text(encoding="utf-8").endswith("\n")
    assert state_file.with_suffix(".tmp").exists() is False


def test_save_state_wraps_os_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "state.json"
    wallpaper = tmp_path / "frame.png"

    def fail_write(*args: object, **kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(
        "dynamic_wallpaper.state.atomic_write_text", fail_write
    )

    with pytest.raises(StateError, match="disk full"):
        save_state(state_file, wallpaper, 1)


def test_save_state_fsyncs_file_and_parent_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    wallpaper = tmp_path / "frame.png"
    wallpaper.touch()
    calls: list[int] = []
    monkeypatch.setattr("dynamic_wallpaper.atomic.os.fsync", calls.append)

    save_state(tmp_path / "state.json", wallpaper, 0)

    assert len(calls) == 2
