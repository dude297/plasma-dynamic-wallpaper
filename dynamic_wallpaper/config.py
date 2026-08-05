"""Configuration loading for dynamic-wallpaper."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .atomic import atomic_write_text


@dataclass(frozen=True)
class Config:
    heic_file: Path
    cache_dir: Path
    screen_ids: tuple[int, ...] | None = None
    schedule_mode: str = "embedded"
    latitude: float | None = None
    longitude: float | None = None


def _parse_assignment(line: str) -> tuple[str, str] | None:
    line = line.strip()

    if not line or line.startswith("#") or "=" not in line:
        return None

    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip()

    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]

    value = os.path.expandvars(os.path.expanduser(value))
    return key, value


def config_path() -> Path:
    """Return the active user configuration path."""
    config_home = Path(
        os.environ.get(
            "XDG_CONFIG_HOME",
            Path.home() / ".config",
        )
    )
    return config_home / "dynamic-wallpaper" / "config"


def load_config(path: Path | None = None) -> Config:
    if path is None:
        path = config_path()

    if not path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    values: dict[str, str] = {}

    for line in path.read_text(encoding="utf-8").splitlines():
        assignment = _parse_assignment(line)

        if assignment is not None:
            key, value = assignment
            values[key] = value

    try:
        heic_file = Path(values["HEIC_FILE"])
        cache_dir = Path(values["CACHE_DIR"])
    except KeyError as exc:
        raise ValueError(f"Missing required setting: {exc.args[0]}") from exc

    screen_ids: tuple[int, ...] | None = None
    schedule_mode: str = "embedded"

    raw_screen_ids = values.get("SCREEN_IDS", "").strip()
    if raw_screen_ids:
        try:
            parsed_screen_ids = tuple(
                int(value.strip())
                for value in raw_screen_ids.split(",")
                if value.strip()
            )
        except ValueError as exc:
            raise ValueError(
                "SCREEN_IDS must be a comma-separated list of integers"
            ) from exc
        screen_ids = parsed_screen_ids

    schedule_mode = values.get("SCHEDULE_MODE", "embedded").strip().casefold()

    def optional_float(key: str) -> float | None:
        raw = values.get(key, "").strip()
        if not raw:
            return None
        try:
            return float(raw)
        except ValueError as exc:
            raise ValueError(f"{key} must be numeric") from exc

    return Config(
        heic_file=heic_file,
        cache_dir=cache_dir,
        screen_ids=screen_ids,
        schedule_mode=schedule_mode,
        latitude=optional_float("LATITUDE"),
        longitude=optional_float("LONGITUDE"),
    )


def update_config_values(
    values: dict[str, str], path: Path | None = None
) -> Path:
    """Atomically update selected assignments while preserving other lines."""
    path = path or config_path()
    existing = (
        path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    )
    pending = dict(values)
    output: list[str] = []

    for line in existing:
        assignment = _parse_assignment(line)
        if assignment is None:
            output.append(line)
            continue
        key, _ = assignment
        if key in pending:
            output.append(f"{key}={pending.pop(key)}")
        else:
            output.append(line)

    if pending and output and output[-1].strip():
        output.append("")
    output.extend(f"{key}={value}" for key, value in pending.items())

    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, "\n".join(output) + "\n", mode=0o600)
    return path


def validate_config(config: Config) -> None:
    """Validate configuration values before wallpaper processing starts."""
    if config.heic_file.suffix.casefold() != ".heic":
        raise ValueError(
            f"HEIC_FILE must point to a .heic file: {config.heic_file}"
        )

    if config.screen_ids is not None:
        if not config.screen_ids:
            raise ValueError("SCREEN_IDS must contain at least one screen")
        if any(screen_id < 0 for screen_id in config.screen_ids):
            raise ValueError("SCREEN_IDS cannot contain negative values")
        if len(set(config.screen_ids)) != len(config.screen_ids):
            raise ValueError("SCREEN_IDS cannot contain duplicates")

    if config.schedule_mode not in {"embedded", "solar"}:
        raise ValueError("SCHEDULE_MODE must be either embedded or solar")

    if config.schedule_mode == "solar":
        if config.latitude is None or config.longitude is None:
            raise ValueError(
                "LATITUDE and LONGITUDE are required for solar scheduling"
            )
        if not -90 <= config.latitude <= 90:
            raise ValueError("LATITUDE must be between -90 and 90")
        if not -180 <= config.longitude <= 180:
            raise ValueError("LONGITUDE must be between -180 and 180")

    if config.cache_dir.exists() and not config.cache_dir.is_dir():
        raise ValueError(
            f"CACHE_DIR must point to a directory: {config.cache_dir}"
        )
