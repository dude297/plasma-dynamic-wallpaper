"""Configuration loading for dynamic-wallpaper."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    heic_file: Path
    cache_dir: Path


def _parse_assignment(line: str) -> tuple[str, str] | None:
    line = line.strip()

    if not line or line.startswith("#") or "=" not in line:
        return None

    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip()

    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {"'", '"'}
    ):
        value = value[1:-1]

    value = os.path.expandvars(os.path.expanduser(value))
    return key, value


def load_config(path: Path | None = None) -> Config:
    if path is None:
        config_home = Path(
            os.environ.get(
                "XDG_CONFIG_HOME",
                Path.home() / ".config",
            )
        )
        path = config_home / "dynamic-wallpaper" / "config"

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
        raise ValueError(
            f"Missing required setting: {exc.args[0]}"
        ) from exc

    return Config(
        heic_file=heic_file,
        cache_dir=cache_dir,
    )
