"""Recover the wallpaper after KDE Plasma Shell restarts."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from time import sleep

from .logging import get_logger


logger = get_logger("watchdog")
_QDBUS_TIMEOUT_SECONDS = 10


class WatchdogError(RuntimeError):
    """Raised when the Plasma session watchdog cannot run."""


def plasma_name_owner() -> str | None:
    """Return the current D-Bus owner for Plasma Shell, if available."""
    qdbus = shutil.which("qdbus6")
    if qdbus is None:
        raise WatchdogError("qdbus6 was not found")

    try:
        completed = subprocess.run(
            [
                qdbus,
                "org.freedesktop.DBus",
                "/org/freedesktop/DBus",
                "org.freedesktop.DBus.GetNameOwner",
                "org.kde.plasmashell",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=_QDBUS_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise WatchdogError("Plasma D-Bus owner query timed out") from exc
    except subprocess.CalledProcessError:
        return None

    owner = completed.stdout.strip()
    return owner or None


def trigger_wallpaper_service() -> None:
    """Ask systemd to start the synchronized wallpaper one-shot service."""
    try:
        subprocess.run(
            [
                "systemctl",
                "--user",
                "start",
                "--no-block",
                "dynamic-wallpaper.service",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=_QDBUS_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as exc:
        raise WatchdogError("systemctl was not found") from exc
    except subprocess.TimeoutExpired as exc:
        raise WatchdogError("wallpaper recovery request timed out") from exc
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or exc.stdout.strip()
        raise WatchdogError(
            message or "could not start dynamic-wallpaper.service"
        ) from exc


def watch_plasma(
    trigger: Callable[[], None] = trigger_wallpaper_service,
    *,
    interval: float = 2.0,
    owner_query: Callable[[], str | None] = plasma_name_owner,
    sleep_fn: Callable[[float], None] = sleep,
    max_checks: int | None = None,
) -> None:
    """Watch the Plasma D-Bus owner and trigger recovery after restarts."""
    if interval <= 0:
        raise ValueError("watchdog interval must be positive")
    if max_checks is not None and max_checks < 0:
        raise ValueError("watchdog max_checks cannot be negative")

    previous_owner = owner_query()
    logger.info(
        "Plasma session watchdog started; current owner: %s",
        previous_owner or "unavailable",
    )
    checks = 0

    while max_checks is None or checks < max_checks:
        sleep_fn(interval)
        checks += 1
        current_owner = owner_query()

        if current_owner is None:
            if previous_owner is not None:
                logger.warning("Plasma Shell left D-Bus; waiting for recovery")
            previous_owner = None
            continue

        if previous_owner is None:
            logger.info(
                "Plasma Shell returned on D-Bus as %s; reapplying wallpaper",
                current_owner,
            )
            try:
                trigger()
            except WatchdogError as exc:
                logger.error("Could not request wallpaper recovery: %s", exc)
        elif current_owner != previous_owner:
            logger.info(
                "Plasma Shell D-Bus owner changed from %s to %s; "
                "reapplying wallpaper",
                previous_owner,
                current_owner,
            )
            try:
                trigger()
            except WatchdogError as exc:
                logger.error("Could not request wallpaper recovery: %s", exc)

        previous_owner = current_owner
