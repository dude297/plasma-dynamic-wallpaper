"""Persist the last successfully applied wallpaper."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class StateError(RuntimeError):
    """Raised when wallpaper state cannot be saved."""


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        # A damaged state file should never prevent wallpaper updates.
        return {}

    return data if isinstance(data, dict) else {}


def is_current(path: Path, wallpaper: Path) -> bool:
    state = load_state(path)

    saved_wallpaper = state.get("wallpaper")

    if not isinstance(saved_wallpaper, str):
        return False

    try:
        return Path(saved_wallpaper).resolve() == wallpaper.resolve()
    except OSError:
        return False


def save_state(
    path: Path,
    wallpaper: Path,
    frame_index: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    state = {
        "wallpaper": str(wallpaper.resolve()),
        "frame_index": frame_index,
        "applied_at": datetime.now(timezone.utc).isoformat(),
    }

    temporary_path = path.with_suffix(".tmp")

    try:
        temporary_path.write_text(
            json.dumps(state, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(path)
    except OSError as exc:
        raise StateError(f"Could not save wallpaper state: {exc}") from exc
