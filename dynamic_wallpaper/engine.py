"""Application orchestration for dynamic-wallpaper."""

from __future__ import annotations

import json
from time import perf_counter
from datetime import datetime
from pathlib import Path
from typing import Any

from .cache import (
    cache_is_current,
    extract_frames,
    find_frames,
    prepare_frames,
)
from .config import Config
from .logging import get_logger
from .metadata import load_h24_metadata
from .plasma import set_wallpaper
from .scheduler import format_schedule, select_frame
from .state import is_current, load_state, save_state


logger = get_logger("engine")


class WallpaperEngine:
    """Coordinate metadata, cache, scheduling, state, and Plasma updates."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self._metadata: Any | None = None
        self._frames: list[Path] | None = None

    @property
    def metadata(self) -> Any:
        """Decode and cache the wallpaper's embedded Apple metadata."""
        if self._metadata is None:
            if not self.config.heic_file.is_file():
                raise FileNotFoundError(
                    f"HEIC wallpaper not found: {self.config.heic_file}"
                )

            started = perf_counter()
            logger.info("Decoding HEIC metadata: %s", self.config.heic_file)
            self._metadata = load_h24_metadata(
                self.config.heic_file,
                self.config.cache_dir,
            )
            logger.info(
                "Metadata decoded in %.1f ms",
                (perf_counter() - started) * 1000,
            )

        return self._metadata

    @property
    def frames(self) -> list[Path]:
        """Prepare and cache extracted wallpaper frames."""
        if self._frames is None:
            started = perf_counter()
            logger.info(
                "Preparing frame cache: source=%s cache=%s",
                self.config.heic_file,
                self.config.cache_dir,
            )
            self._frames = prepare_frames(
                self.config.heic_file,
                self.config.cache_dir,
            )
            logger.info(
                "Prepared %d frame(s) in %.1f ms",
                len(self._frames),
                (perf_counter() - started) * 1000,
            )

        return self._frames

    @property
    def state_file(self) -> Path:
        """Return the state file shared by the active wallpaper cache."""
        return self.config.cache_dir.parent / "state.json"

    def status(self) -> list[str]:
        """Return the persisted status of the last wallpaper update."""
        state = load_state(self.state_file)
        wallpaper = state.get("wallpaper")
        frame_index = state.get("frame_index")
        applied_at = state.get("applied_at")

        lines = [
            f"Source HEIC: {self.config.heic_file}",
            f"Cache directory: {self.config.cache_dir}",
            f"State file: {self.state_file}",
        ]

        if not isinstance(wallpaper, str):
            lines.append("Last applied: no recorded wallpaper")
            return lines

        lines.append(f"Last wallpaper: {wallpaper}")
        lines.append(
            "Last frame: "
            + (str(frame_index) if isinstance(frame_index, int) else "unknown")
        )
        lines.append(
            "Applied at: "
            + (applied_at if isinstance(applied_at, str) else "unknown")
        )
        lines.append(
            "Wallpaper file: "
            + ("present" if Path(wallpaper).is_file() else "missing")
        )
        return lines

    def cache_status(self) -> list[str]:
        """Return cache freshness and frame inventory details."""
        frames = find_frames(self.config.cache_dir)
        current = self.config.heic_file.is_file() and cache_is_current(
            self.config.heic_file, self.config.cache_dir
        )

        return [
            f"Cache directory: {self.config.cache_dir}",
            f"Cached frames: {len(frames)}",
            f"Cache current: {'yes' if current else 'no'}",
        ]

    def rebuild_cache(self) -> str:
        """Force frame extraction even when the cache appears current."""
        started = perf_counter()
        logger.info("Forcing cache rebuild: %s", self.config.cache_dir)
        self._frames = extract_frames(
            self.config.heic_file,
            self.config.cache_dir,
        )
        logger.info(
            "Cache rebuild completed with %d frame(s) in %.1f ms",
            len(self._frames),
            (perf_counter() - started) * 1000,
        )
        return (
            f"Rebuilt {len(self._frames)} frame(s) in {self.config.cache_dir}"
        )

    def inspect(self) -> str:
        """Return decoded metadata as formatted JSON."""
        return json.dumps(
            self.metadata,
            indent=2,
            default=_json_default,
        )

    def schedule(self) -> list[str]:
        """Return the formatted embedded schedule and appearance metadata."""
        lines = format_schedule(self.metadata)
        appearance = self.metadata.get("ap")

        if isinstance(appearance, dict):
            lines.extend(
                [
                    "",
                    (
                        "Appearance alternatives: "
                        f"light={appearance.get('l')}, "
                        f"dark={appearance.get('d')}"
                    ),
                ]
            )

        return lines

    def extract(self) -> str:
        """Prepare frames without changing the desktop wallpaper."""
        return (
            f"Prepared {len(self.frames)} frame(s) in {self.config.cache_dir}"
        )

    def apply(
        self,
        selected_time: datetime,
        *,
        dry_run: bool = False,
        force: bool = False,
    ) -> list[str]:
        """Select and optionally apply the correct wallpaper frame."""
        operation_started = perf_counter()
        selection_started = perf_counter()
        index, wallpaper, entry = select_frame(
            self.frames,
            self.metadata,
            selected_time,
        )
        logger.info(
            "Selected frame %d (%s) for %s in %.1f ms",
            index,
            wallpaper,
            selected_time.isoformat(),
            (perf_counter() - selection_started) * 1000,
        )

        last_index = len(self.frames) - 1
        output: list[str] = []

        if dry_run:
            logger.info("Dry run; wallpaper will not be changed")
            action = (
                "Would keep"
                if is_current(self.state_file, wallpaper)
                else "Would apply"
            )
            output.append(f"{action} frame {index}/{last_index}: {wallpaper}")
        elif not force and is_current(self.state_file, wallpaper):
            logger.info("Skipping frame because persisted state is current")
            output.append(
                f"Skipped frame {index}/{last_index}: already applied"
            )
        else:
            apply_started = perf_counter()
            logger.info(
                "Applying wallpaper%s: %s",
                " (forced)" if force else "",
                wallpaper,
            )
            set_wallpaper(wallpaper, self.config.screen_ids)
            logger.info(
                "Plasma wallpaper update completed in %.1f ms",
                (perf_counter() - apply_started) * 1000,
            )
            save_state(self.state_file, wallpaper, index)
            logger.debug("Saved state to %s", self.state_file)
            output.append(f"Applied frame {index}/{last_index}: {wallpaper}")

        start_hour, start_minute = divmod(entry.minutes, 60)
        output.append(
            f"Time {selected_time:%H:%M}; schedule entry "
            f"{start_hour:02d}:{start_minute:02d}"
        )

        logger.info(
            "Wallpaper operation completed in %.1f ms",
            (perf_counter() - operation_started) * 1000,
        )
        return output


def _json_default(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"type": "bytes", "hex": value.hex()}

    if isinstance(value, datetime):
        return value.isoformat()

    raise TypeError(f"Cannot serialize {type(value).__name__}")
