"""Select HEIC frames using Apple Dynamic Desktop metadata."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


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


def select_frame(
    frames: list[Path],
    metadata: Any,
    now: datetime,
) -> tuple[int, Path, ScheduleEntry]:
    if not frames:
        raise ScheduleError("No extracted frames are available")

    entries = parse_time_schedule(metadata)
    current_minutes = now.hour * 60 + now.minute

    # Wrap to the previous day's last entry before midnight's
    # first explicit schedule entry.
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


def format_schedule(metadata: Any) -> list[str]:
    output: list[str] = []

    for entry in parse_time_schedule(metadata):
        hours, minutes = divmod(entry.minutes, 60)
        output.append(
            f"{hours:02d}:{minutes:02d} -> frame {entry.frame_index}"
        )

    return output
