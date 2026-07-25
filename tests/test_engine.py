"""Tests for application orchestration in WallpaperEngine."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from dynamic_wallpaper.config import Config
from dynamic_wallpaper.engine import WallpaperEngine, _json_default


def make_engine(tmp_path: Path) -> WallpaperEngine:
    return WallpaperEngine(
        Config(
            heic_file=tmp_path / "wallpaper.heic",
            cache_dir=tmp_path / "cache" / "frames",
        )
    )


def test_metadata_checks_source_file_exists(tmp_path: Path) -> None:
    engine = make_engine(tmp_path)

    with pytest.raises(FileNotFoundError, match="HEIC wallpaper not found"):
        _ = engine.metadata


def test_metadata_is_decoded_only_once(tmp_path: Path) -> None:
    engine = make_engine(tmp_path)
    engine.config.heic_file.touch()
    metadata = {"ti": [{"t": 0.0, "i": 0}]}

    with patch(
        "dynamic_wallpaper.engine.decode_h24",
        return_value=metadata,
    ) as decode:
        assert engine.metadata is metadata
        assert engine.metadata is metadata

    decode.assert_called_once_with(engine.config.heic_file)


def test_frames_are_prepared_only_once(tmp_path: Path) -> None:
    engine = make_engine(tmp_path)
    frames = [tmp_path / "frame-0.png"]

    with patch(
        "dynamic_wallpaper.engine.prepare_frames",
        return_value=frames,
    ) as prepare:
        assert engine.frames is frames
        assert engine.frames is frames

    prepare.assert_called_once_with(
        engine.config.heic_file,
        engine.config.cache_dir,
    )


def test_state_file_is_next_to_active_cache_directory(tmp_path: Path) -> None:
    engine = make_engine(tmp_path)

    assert engine.state_file == tmp_path / "cache" / "state.json"


def test_cache_status_reports_current_cache(tmp_path: Path) -> None:
    engine = make_engine(tmp_path)
    engine.config.heic_file.touch()
    engine.config.cache_dir.mkdir(parents=True)
    (engine.config.cache_dir / "frame-1.png").touch()
    (engine.config.cache_dir / "frame-2.png").touch()

    with patch("dynamic_wallpaper.engine.cache_is_current", return_value=True):
        lines = engine.cache_status()

    assert lines == [
        f"Cache directory: {engine.config.cache_dir}",
        "Cached frames: 2",
        "Cache current: yes",
    ]


def test_cache_status_reports_missing_source_as_stale(tmp_path: Path) -> None:
    engine = make_engine(tmp_path)

    with patch("dynamic_wallpaper.engine.cache_is_current") as check_current:
        lines = engine.cache_status()

    assert lines[-2:] == ["Cached frames: 0", "Cache current: no"]
    check_current.assert_not_called()


def test_rebuild_cache_forces_extraction(tmp_path: Path) -> None:
    engine = make_engine(tmp_path)
    frames = [tmp_path / "frame-1.png", tmp_path / "frame-2.png"]

    with patch(
        "dynamic_wallpaper.engine.extract_frames",
        return_value=frames,
    ) as extract:
        result = engine.rebuild_cache()

    assert result == f"Rebuilt 2 frame(s) in {engine.config.cache_dir}"
    assert engine._frames == frames
    extract.assert_called_once_with(
        engine.config.heic_file,
        engine.config.cache_dir,
    )


def test_inspect_formats_metadata_as_json(tmp_path: Path) -> None:
    engine = make_engine(tmp_path)
    engine._metadata = {
        "payload": b"\x01\x02",
        "created": datetime(2026, 7, 23, 12, 30),
    }

    assert engine.inspect() == (
        "{\n"
        '  "payload": {\n'
        '    "type": "bytes",\n'
        '    "hex": "0102"\n'
        "  },\n"
        '  "created": "2026-07-23T12:30:00"\n'
        "}"
    )


def test_schedule_adds_appearance_alternatives(tmp_path: Path) -> None:
    engine = make_engine(tmp_path)
    engine._metadata = {
        "ti": [{"t": 0.0, "i": 0}],
        "ap": {"l": 2, "d": 6},
    }

    assert engine.schedule() == [
        "00:00 -> frame 0",
        "",
        "Appearance alternatives: light=2, dark=6",
    ]


def test_schedule_omits_invalid_appearance_metadata(tmp_path: Path) -> None:
    engine = make_engine(tmp_path)
    engine._metadata = {
        "ti": [{"t": 0.0, "i": 0}],
        "ap": "invalid",
    }

    assert engine.schedule() == ["00:00 -> frame 0"]


def test_extract_reports_prepared_frame_count(tmp_path: Path) -> None:
    engine = make_engine(tmp_path)
    engine._frames = [
        tmp_path / "frame-0.png",
        tmp_path / "frame-1.png",
    ]

    assert engine.extract() == (
        f"Prepared 2 frame(s) in {engine.config.cache_dir}"
    )


def test_apply_dry_run_reports_new_frame_without_side_effects(
    tmp_path: Path,
) -> None:
    engine = make_engine(tmp_path)
    frames = [tmp_path / "frame-0.png", tmp_path / "frame-1.png"]
    engine._frames = frames
    engine._metadata = {"ti": [{"t": 0.5, "i": 1}]}
    selected_time = datetime(2026, 7, 23, 12, 0)

    with (
        patch("dynamic_wallpaper.engine.is_current", return_value=False),
        patch("dynamic_wallpaper.engine.set_wallpaper") as set_wallpaper,
        patch("dynamic_wallpaper.engine.save_state") as save_state,
    ):
        output = engine.apply(selected_time, dry_run=True)

    assert output == [
        f"Would apply frame 1/1: {frames[1]}",
        "Time 12:00; schedule entry 12:00",
    ]
    set_wallpaper.assert_not_called()
    save_state.assert_not_called()


def test_apply_dry_run_reports_current_frame(tmp_path: Path) -> None:
    engine = make_engine(tmp_path)
    frame = tmp_path / "frame-0.png"
    engine._frames = [frame]
    engine._metadata = {"ti": [{"t": 0.0, "i": 0}]}

    with patch("dynamic_wallpaper.engine.is_current", return_value=True):
        output = engine.apply(
            datetime(2026, 7, 23, 8, 15),
            dry_run=True,
        )

    assert output[0] == f"Would keep frame 0/0: {frame}"


def test_apply_skips_frame_that_is_already_current(tmp_path: Path) -> None:
    engine = make_engine(tmp_path)
    frame = tmp_path / "frame-0.png"
    engine._frames = [frame]
    engine._metadata = {"ti": [{"t": 0.0, "i": 0}]}

    with (
        patch("dynamic_wallpaper.engine.is_current", return_value=True),
        patch("dynamic_wallpaper.engine.set_wallpaper") as set_wallpaper,
        patch("dynamic_wallpaper.engine.save_state") as save_state,
    ):
        output = engine.apply(datetime(2026, 7, 23, 8, 15))

    assert output[0] == "Skipped frame 0/0: already applied"
    set_wallpaper.assert_not_called()
    save_state.assert_not_called()


def test_apply_sets_wallpaper_and_saves_state(tmp_path: Path) -> None:
    engine = make_engine(tmp_path)
    frame = tmp_path / "frame-0.png"
    engine._frames = [frame]
    engine._metadata = {"ti": [{"t": 0.0, "i": 0}]}

    with (
        patch("dynamic_wallpaper.engine.is_current", return_value=False),
        patch("dynamic_wallpaper.engine.set_wallpaper") as set_wallpaper,
        patch("dynamic_wallpaper.engine.save_state") as save_state,
    ):
        output = engine.apply(datetime(2026, 7, 23, 8, 15))

    assert output[0] == f"Applied frame 0/0: {frame}"
    set_wallpaper.assert_called_once_with(frame)
    save_state.assert_called_once_with(engine.state_file, frame, 0)


def test_force_applies_even_when_frame_is_current(tmp_path: Path) -> None:
    engine = make_engine(tmp_path)
    frame = tmp_path / "frame-0.png"
    engine._frames = [frame]
    engine._metadata = {"ti": [{"t": 0.0, "i": 0}]}

    with (
        patch("dynamic_wallpaper.engine.is_current", return_value=True),
        patch("dynamic_wallpaper.engine.set_wallpaper") as set_wallpaper,
        patch("dynamic_wallpaper.engine.save_state") as save_state,
    ):
        output = engine.apply(
            datetime(2026, 7, 23, 8, 15),
            force=True,
        )

    assert output[0] == f"Applied frame 0/0: {frame}"
    set_wallpaper.assert_called_once_with(frame)
    save_state.assert_called_once_with(engine.state_file, frame, 0)


def test_json_default_rejects_unsupported_values() -> None:
    with pytest.raises(TypeError, match="Cannot serialize object"):
        _json_default(object())


def test_status_reports_missing_state(tmp_path: Path) -> None:
    config = Config(tmp_path / "wallpaper.heic", tmp_path / "cache" / "frames")
    engine = WallpaperEngine(config)

    assert engine.status()[-1] == "Last applied: no recorded wallpaper"


def test_status_reports_persisted_wallpaper(tmp_path: Path) -> None:
    wallpaper = tmp_path / "frame.png"
    wallpaper.write_bytes(b"png")
    config = Config(tmp_path / "wallpaper.heic", tmp_path / "cache" / "frames")
    engine = WallpaperEngine(config)
    engine.state_file.parent.mkdir(parents=True)
    engine.state_file.write_text(
        json.dumps(
            {
                "wallpaper": str(wallpaper),
                "frame_index": 3,
                "applied_at": "2026-07-24T20:30:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    lines = engine.status()

    assert "Last wallpaper: " + str(wallpaper) in lines
    assert "Last frame: 3" in lines
    assert "Applied at: 2026-07-24T20:30:00+00:00" in lines
    assert "Wallpaper file: present" in lines
