"""Per-user setup for pipx and wheel installations."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from importlib.resources import files
from pathlib import Path


class InstallError(RuntimeError):
    """Raised when per-user setup cannot be completed."""


def _config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def _data_home() -> Path:
    return Path(
        os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
    )


def _command_path() -> str:
    return shutil.which("dynamic-wallpaper") or str(
        Path(sys.argv[0]).resolve()
    )


def install_user(*, enable_timer: bool = True) -> tuple[str, ...]:
    """Install config and systemd units for the current user."""
    config_dir = _config_home() / "dynamic-wallpaper"
    systemd_dir = _config_home() / "systemd" / "user"
    config_path = config_dir / "config"
    service_path = systemd_dir / "dynamic-wallpaper.service"
    timer_path = systemd_dir / "dynamic-wallpaper.timer"
    watch_path = systemd_dir / "dynamic-wallpaper-watch.service"

    config_dir.mkdir(parents=True, exist_ok=True)
    systemd_dir.mkdir(parents=True, exist_ok=True)

    package_data = files("dynamic_wallpaper.data")
    if not config_path.exists():
        config_path.write_text(
            package_data.joinpath("config.example").read_text(
                encoding="utf-8"
            ),
            encoding="utf-8",
        )

    service = package_data.joinpath("dynamic-wallpaper.service").read_text(
        encoding="utf-8"
    )
    service = service.replace("@DYNAMIC_WALLPAPER_COMMAND@", _command_path())
    service_path.write_text(service, encoding="utf-8")
    watch_service = package_data.joinpath(
        "dynamic-wallpaper-watch.service"
    ).read_text(encoding="utf-8")
    watch_service = watch_service.replace(
        "@DYNAMIC_WALLPAPER_COMMAND@", _command_path()
    )
    watch_path.write_text(watch_service, encoding="utf-8")
    timer_path.write_text(
        package_data.joinpath("dynamic-wallpaper.timer").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )

    lines = [
        f"Configuration: {config_path}",
        f"Service: {service_path}",
        f"Timer: {timer_path}",
        f"Watchdog: {watch_path}",
    ]

    if enable_timer:
        try:
            subprocess.run(
                ["systemctl", "--user", "daemon-reload"],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                [
                    "systemctl",
                    "--user",
                    "enable",
                    "--now",
                    "dynamic-wallpaper.timer",
                    "dynamic-wallpaper-watch.service",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            raise InstallError(
                "could not enable the user timer; run setup again inside a "
                "graphical session or use --setup-no-enable"
            ) from exc
        lines.append("Timer enabled: yes")
        lines.append("Watchdog enabled: yes")
    else:
        lines.append("Timer enabled: no")
        lines.append("Watchdog enabled: no")

    wallpaper_dir = _data_home() / "dynamic-wallpaper" / "wallpapers"
    lines.append(f"Wallpaper library: {wallpaper_dir}")
    return tuple(lines)
