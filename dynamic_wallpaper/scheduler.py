"""Select HEIC frames using embedded or solar-aligned schedules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .solar import calculate_solar_events, timezone_offset_for


class ScheduleError(RuntimeError):
    """Raised when the embedded wallpaper schedule is invalid."""


@dataclass(frozen=True)
class ScheduleEntry:
    time_fraction: float
    frame_index: int

    @property
    def minutes(self) -> int:
        return round(self.time_fraction * 1440)


def parse_time_schedule(metadata: Any) -> list[ScheduleEntry]:
    if not isinstance(metadata, dict):
        raise ScheduleError("Dynamic metadata must be a dictionary")

    raw_entries = metadata.get("ti")

    if not isinstance(raw_entries, list) or not raw_entries:
        raise ScheduleError("No time schedule found in HEIC metadata")

    entries: list[ScheduleEntry] = []

    for item in raw_entries:
        if not isinstance(item, dict):
            raise ScheduleError("Invalid schedule entry")

        time_fraction = item.get("t")
        frame_index = item.get("i")

        if not isinstance(time_fraction, (int, float)):
            raise ScheduleError("Schedule time must be numeric")

        if not isinstance(frame_index, int):
            raise ScheduleError("Frame index must be an integer")

        if not 0 <= float(time_fraction) < 1:
            raise ScheduleError(
                f"Time fraction is outside the day: {time_fraction}"
            )

        if frame_index < 0:
            raise ScheduleError(
                f"Frame index cannot be negative: {frame_index}"
            )

        entries.append(
            ScheduleEntry(
                time_fraction=float(time_fraction),
                frame_index=frame_index,
            )
        )

    return sorted(entries, key=lambda entry: entry.time_fraction)


def resolve_time_schedule(
    metadata: Any,
    now: datetime,
    *,
    latitude: float | None = None,
    longitude: float | None = None,
) -> list[ScheduleEntry]:
    """Return the embedded schedule or a location-aligned solar schedule."""
    entries = parse_time_schedule(metadata)
    if latitude is None and longitude is None:
        return entries
    if latitude is None or longitude is None:
        raise ScheduleError(
            "Both latitude and longitude are required for solar scheduling"
        )

    try:
        events = calculate_solar_events(
            now.date(),
            latitude,
            longitude,
            timezone_offset_minutes=timezone_offset_for(now),
        )
    except RuntimeError as exc:
        raise ScheduleError(str(exc)) from exc

    source_anchors = (0, 240, 720, 1200, 1440)
    target_anchors = (
        0,
        events.civil_dawn,
        events.solar_noon,
        events.civil_dusk,
        1440,
    )

    return [
        ScheduleEntry(
            time_fraction=_warp_minutes(
                entry.minutes, source_anchors, target_anchors
            )
            / 1440,
            frame_index=entry.frame_index,
        )
        for entry in entries
    ]


def select_frame(
    frames: list[Path],
    metadata: Any,
    now: datetime,
    *,
    latitude: float | None = None,
    longitude: float | None = None,
) -> tuple[int, Path, ScheduleEntry]:
    if not frames:
        raise ScheduleError("No extracted frames are available")

    entries = resolve_time_schedule(
        metadata,
        now,
        latitude=latitude,
        longitude=longitude,
    )
    current_minutes = now.hour * 60 + now.minute

    selected = entries[-1]

    for entry in entries:
        if entry.minutes <= current_minutes:
            selected = entry
        else:
            break

    if selected.frame_index >= len(frames):
        raise ScheduleError(
            f"Schedule references frame {selected.frame_index}, "
            f"but only {len(frames)} frames exist"
        )

    return (
        selected.frame_index,
        frames[selected.frame_index],
        selected,
    )


def format_schedule(
    metadata: Any,
    now: datetime | None = None,
    *,
    latitude: float | None = None,
    longitude: float | None = None,
) -> list[str]:
    now = now or datetime.now().astimezone()
    output: list[str] = []

    for entry in resolve_time_schedule(
        metadata,
        now,
        latitude=latitude,
        longitude=longitude,
    ):
        hours, minutes = divmod(entry.minutes, 60)
        output.append(
            f"{hours:02d}:{minutes:02d} -> frame {entry.frame_index}"
        )

    return output


def _warp_minutes(
    minute: int,
    source_anchors: tuple[int, ...],
    target_anchors: tuple[int, ...],
) -> int:
    for index in range(len(source_anchors) - 1):
        source_start = source_anchors[index]
        source_end = source_anchors[index + 1]
        if minute <= source_end:
            progress = (minute - source_start) / (source_end - source_start)
            target_start = target_anchors[index]
            target_end = target_anchors[index + 1]
            return round(target_start + progress * (target_end - target_start))
    return target_anchors[-1]
