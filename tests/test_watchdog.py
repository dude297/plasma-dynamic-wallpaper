"""Tests for Plasma Shell restart recovery."""

from __future__ import annotations

import subprocess
from unittest.mock import Mock, patch

import pytest

from dynamic_wallpaper.watchdog import (
    WatchdogError,
    plasma_name_owner,
    trigger_wallpaper_service,
    watch_plasma,
)


def test_plasma_name_owner_returns_owner() -> None:
    completed = subprocess.CompletedProcess(["qdbus6"], 0, ":1.42\n", "")
    with (
        patch(
            "dynamic_wallpaper.watchdog.shutil.which",
            return_value="/usr/bin/qdbus6",
        ),
        patch(
            "dynamic_wallpaper.watchdog.subprocess.run",
            return_value=completed,
        ) as run,
    ):
        assert plasma_name_owner() == ":1.42"

    assert "org.freedesktop.DBus.GetNameOwner" in run.call_args.args[0]


def test_plasma_name_owner_returns_none_when_name_is_missing() -> None:
    error = subprocess.CalledProcessError(1, ["qdbus6"])
    with (
        patch(
            "dynamic_wallpaper.watchdog.shutil.which",
            return_value="qdbus6",
        ),
        patch(
            "dynamic_wallpaper.watchdog.subprocess.run",
            side_effect=error,
        ),
    ):
        assert plasma_name_owner() is None


def test_trigger_wallpaper_service_uses_nonblocking_systemd_start() -> None:
    with patch("dynamic_wallpaper.watchdog.subprocess.run") as run:
        trigger_wallpaper_service()

    assert run.call_args.args[0] == [
        "systemctl",
        "--user",
        "start",
        "--no-block",
        "dynamic-wallpaper.service",
    ]


def test_watch_plasma_triggers_when_owner_returns() -> None:
    owners = iter([":1.1", None, ":1.2", ":1.2"])
    trigger = Mock()

    watch_plasma(
        trigger,
        interval=0.01,
        owner_query=lambda: next(owners),
        sleep_fn=Mock(),
        max_checks=3,
    )

    trigger.assert_called_once_with()


def test_watch_plasma_triggers_on_direct_owner_change() -> None:
    owners = iter([":1.1", ":1.2"])
    trigger = Mock()

    watch_plasma(
        trigger,
        interval=0.01,
        owner_query=lambda: next(owners),
        sleep_fn=Mock(),
        max_checks=1,
    )

    trigger.assert_called_once_with()


def test_watch_plasma_rejects_invalid_interval() -> None:
    with pytest.raises(ValueError, match="interval must be positive"):
        watch_plasma(interval=0)


def test_plasma_name_owner_requires_qdbus6() -> None:
    with (
        patch("dynamic_wallpaper.watchdog.shutil.which", return_value=None),
        pytest.raises(WatchdogError, match="qdbus6 was not found"),
    ):
        plasma_name_owner()
