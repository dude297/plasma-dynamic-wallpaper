"""Tests for dynamic wallpaper schedule parsing and frame selection."""

from datetime import datetime
from pathlib import Path

import pytest

from dynamic_wallpaper.scheduler import (
    ScheduleEntry,
    ScheduleError,
    format_schedule,
    parse_time_schedule,
    select_frame,
)


def make_frames(count: int) -> list[Path]:
    return [Path(f"/tmp/frame-{index}.png") for index in range(count)]


def test_schedule_entry_converts_fraction_to_minutes() -> None:
    entry = ScheduleEntry(time_fraction=0.5, frame_index=2)

    assert entry.minutes == 720


def test_parse_time_schedule_sorts_entries() -> None:
    metadata = {
        "ti": [
            {"t": 0.75, "i": 2},
            {"t": 0.25, "i": 0},
            {"t": 0.50, "i": 1},
        ]
    }

    entries = parse_time_schedule(metadata)

    assert [entry.frame_index for entry in entries] == [0, 1, 2]
    assert [entry.minutes for entry in entries] == [360, 720, 1080]


@pytest.mark.parametrize(
    ("metadata", "message"),
    [
        (None, "must be a dictionary"),
        ({}, "No time schedule"),
        ({"ti": []}, "No time schedule"),
        ({"ti": "invalid"}, "No time schedule"),
        ({"ti": ["invalid"]}, "Invalid schedule entry"),
        ({"ti": [{"t": "noon", "i": 0}]}, "time must be numeric"),
        ({"ti": [{"t": 0.5, "i": "0"}]}, "index must be an integer"),
        ({"ti": [{"t": -0.1, "i": 0}]}, "outside the day"),
        ({"ti": [{"t": 1.0, "i": 0}]}, "outside the day"),
        ({"ti": [{"t": 0.5, "i": -1}]}, "cannot be negative"),
    ],
)
def test_parse_time_schedule_rejects_invalid_metadata(
    metadata: object,
    message: str,
) -> None:
    with pytest.raises(ScheduleError, match=message):
        parse_time_schedule(metadata)


def test_select_frame_uses_exact_transition_time() -> None:
    frames = make_frames(3)
    metadata = {
        "ti": [
            {"t": 0.0, "i": 0},
            {"t": 0.5, "i": 1},
            {"t": 0.75, "i": 2},
        ]
    }

    index, path, entry = select_frame(
        frames,
        metadata,
        datetime(2026, 7, 23, 12, 0),
    )

    assert index == 1
    assert path == frames[1]
    assert entry.minutes == 720


def test_select_frame_uses_previous_entry_before_transition() -> None:
    frames = make_frames(3)
    metadata = {
        "ti": [
            {"t": 0.0, "i": 0},
            {"t": 0.5, "i": 1},
            {"t": 0.75, "i": 2},
        ]
    }

    index, path, entry = select_frame(
        frames,
        metadata,
        datetime(2026, 7, 23, 11, 59),
    )

    assert index == 0
    assert path == frames[0]
    assert entry.minutes == 0


def test_select_frame_wraps_to_last_entry_before_first_transition() -> None:
    frames = make_frames(3)
    metadata = {
        "ti": [
            {"t": 0.25, "i": 0},
            {"t": 0.5, "i": 1},
            {"t": 0.75, "i": 2},
        ]
    }

    index, path, entry = select_frame(
        frames,
        metadata,
        datetime(2026, 7, 23, 2, 0),
    )

    assert index == 2
    assert path == frames[2]
    assert entry.minutes == 1080


def test_select_frame_rejects_empty_frame_list() -> None:
    metadata = {"ti": [{"t": 0.0, "i": 0}]}

    with pytest.raises(ScheduleError, match="No extracted frames"):
        select_frame(
            [],
            metadata,
            datetime(2026, 7, 23, 12, 0),
        )


def test_select_frame_rejects_out_of_range_frame_reference() -> None:
    frames = make_frames(2)
    metadata = {"ti": [{"t": 0.0, "i": 2}]}

    with pytest.raises(ScheduleError, match="only 2 frames exist"):
        select_frame(
            frames,
            metadata,
            datetime(2026, 7, 23, 12, 0),
        )


def test_format_schedule_returns_readable_lines() -> None:
    metadata = {
        "ti": [
            {"t": 0.5, "i": 1},
            {"t": 0.0, "i": 0},
            {"t": 0.75, "i": 2},
        ]
    }

    assert format_schedule(metadata) == [
        "00:00 -> frame 0",
        "12:00 -> frame 1",
        "18:00 -> frame 2",
    ]


def test_resolve_solar_schedule_preserves_frame_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dynamic_wallpaper import scheduler
    from dynamic_wallpaper.solar import SolarEvents

    metadata = {
        "ti": [
            {"t": 0.0, "i": 0},
            {"t": 240 / 1440, "i": 1},
            {"t": 0.5, "i": 2},
            {"t": 1200 / 1440, "i": 3},
        ]
    }
    monkeypatch.setattr(
        scheduler,
        "calculate_solar_events",
        lambda *args, **kwargs: SolarEvents(360, 780, 1200),
    )
    monkeypatch.setattr(scheduler, "timezone_offset_for", lambda now: -420)

    entries = scheduler.resolve_time_schedule(
        metadata,
        datetime(2026, 8, 4, 12, 0),
        latitude=37.3382,
        longitude=-121.8863,
    )

    assert [entry.frame_index for entry in entries] == [0, 1, 2, 3]
    assert [entry.minutes for entry in entries] == [0, 360, 780, 1200]


def test_select_frame_uses_solar_aligned_transition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dynamic_wallpaper import scheduler
    from dynamic_wallpaper.solar import SolarEvents

    metadata = {
        "ti": [
            {"t": 0.0, "i": 0},
            {"t": 240 / 1440, "i": 1},
            {"t": 0.5, "i": 2},
        ]
    }
    frames = make_frames(3)
    monkeypatch.setattr(
        scheduler,
        "calculate_solar_events",
        lambda *args, **kwargs: SolarEvents(360, 780, 1200),
    )
    monkeypatch.setattr(scheduler, "timezone_offset_for", lambda now: -420)

    index, _, entry = select_frame(
        frames,
        metadata,
        datetime(2026, 8, 4, 6, 0),
        latitude=37.3382,
        longitude=-121.8863,
    )

    assert index == 1
    assert entry.minutes == 360
