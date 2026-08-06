"""Recover the wallpaper after Plasma restarts and system resume."""

from __future__ import annotations

import shutil
import subprocess
import time
from collections.abc import Callable
from time import sleep

from .logging import get_logger

logger = get_logger("watchdog")
_QDBUS_TIMEOUT_SECONDS = 10
_RESUME_GAP_SECONDS = 10.0


class WatchdogError(RuntimeError):
    """Raised when the Plasma session watchdog cannot run."""


def session_uptime() -> float:
    """Return a monotonic clock that includes time spent suspended."""
    clock_boottime = getattr(time, "CLOCK_BOOTTIME", None)
    if clock_boottime is not None:
        return time.clock_gettime(clock_boottime)
    return time.monotonic()


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
    clock_fn: Callable[[], float] = session_uptime,
    resume_gap: float = _RESUME_GAP_SECONDS,
    max_checks: int | None = None,
) -> None:
    """Recover after Plasma restarts and system suspend/resume cycles."""
    if interval <= 0:
        raise ValueError("watchdog interval must be positive")
    if resume_gap <= 0:
        raise ValueError("watchdog resume_gap must be positive")
    if max_checks is not None and max_checks < 0:
        raise ValueError("watchdog max_checks cannot be negative")

    previous_owner = owner_query()
    previous_tick = clock_fn()
    logger.info(
        "Watchdog started: interval=%.1fs resume_gap=%.1fs owner=%s",
        interval,
        resume_gap,
        previous_owner or "unavailable",
    )
    checks = 0

    while max_checks is None or checks < max_checks:
        sleep_fn(interval)
        checks += 1
        current_tick = clock_fn()
        elapsed = current_tick - previous_tick
        previous_tick = current_tick
        resumed = elapsed > interval + resume_gap
        current_owner = owner_query()
        recovery_reason: str | None = None

        if resumed:
            recovery_reason = (
                f"system resumed after an {elapsed:.1f}-second watchdog gap"
            )

        if current_owner is None:
            if previous_owner is not None:
                logger.warning("Plasma Shell left D-Bus; waiting for recovery")
            previous_owner = None
            continue

        if previous_owner is None:
            recovery_reason = (
                f"Plasma Shell returned on D-Bus as {current_owner}"
            )
        elif current_owner != previous_owner:
            recovery_reason = (
                "Plasma Shell D-Bus owner changed from "
                f"{previous_owner} to {current_owner}"
            )

        if recovery_reason is not None:
            logger.info("%s; reapplying wallpaper", recovery_reason)
            try:
                trigger()
            except WatchdogError as exc:
                logger.error(
                    "Wallpaper recovery request failed (%s): %s",
                    recovery_reason,
                    exc,
                )
            else:
                logger.info(
                    "Wallpaper recovery requested successfully: %s",
                    recovery_reason,
                )

        previous_owner = current_owner
