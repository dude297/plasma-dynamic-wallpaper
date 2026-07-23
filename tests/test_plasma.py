"""Tests for KDE Plasma wallpaper integration."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from dynamic_wallpaper.plasma import PlasmaError, set_wallpaper


def test_set_wallpaper_requires_qdbus6(tmp_path: Path) -> None:
    image = tmp_path / "wallpaper.png"

    with patch("dynamic_wallpaper.plasma.shutil.which", return_value=None):
        with pytest.raises(PlasmaError, match="qdbus6 was not found"):
            set_wallpaper(image)


def test_set_wallpaper_invokes_plasma_shell(tmp_path: Path) -> None:
    image = tmp_path / 'wallpaper "day".png'

    with (
        patch(
            "dynamic_wallpaper.plasma.shutil.which",
            return_value="/usr/bin/qdbus6",
        ),
        patch("dynamic_wallpaper.plasma.subprocess.run") as run,
    ):
        set_wallpaper(image)

    run.assert_called_once()
    args = run.call_args.args[0]
    kwargs = run.call_args.kwargs

    assert args[:4] == [
        "/usr/bin/qdbus6",
        "org.kde.plasmashell",
        "/PlasmaShell",
        "org.kde.PlasmaShell.evaluateScript",
    ]
    assert kwargs == {
        "check": True,
        "capture_output": True,
        "text": True,
    }

    script = args[4]
    assert "const allDesktops = desktops();" in script
    assert 'desktop.wallpaperPlugin = "org.kde.image";' in script
    assert 'desktop.writeConfig("Image",' in script
    assert image.resolve().as_uri() in script
    assert '%22day%22' in script


def test_set_wallpaper_uses_stderr_from_failed_command(
    tmp_path: Path,
) -> None:
    error = subprocess.CalledProcessError(
        1,
        ["qdbus6"],
        output="ignored output",
        stderr="Plasma is unavailable\n",
    )

    with (
        patch(
            "dynamic_wallpaper.plasma.shutil.which",
            return_value="/usr/bin/qdbus6",
        ),
        patch(
            "dynamic_wallpaper.plasma.subprocess.run",
            side_effect=error,
        ),
    ):
        with pytest.raises(PlasmaError, match="Plasma is unavailable"):
            set_wallpaper(tmp_path / "wallpaper.png")


def test_set_wallpaper_falls_back_to_stdout_from_failed_command(
    tmp_path: Path,
) -> None:
    error = subprocess.CalledProcessError(
        1,
        ["qdbus6"],
        output="evaluation failed\n",
        stderr="",
    )

    with (
        patch(
            "dynamic_wallpaper.plasma.shutil.which",
            return_value="/usr/bin/qdbus6",
        ),
        patch(
            "dynamic_wallpaper.plasma.subprocess.run",
            side_effect=error,
        ),
    ):
        with pytest.raises(PlasmaError, match="evaluation failed"):
            set_wallpaper(tmp_path / "wallpaper.png")


def test_set_wallpaper_uses_generic_message_for_empty_failure(
    tmp_path: Path,
) -> None:
    error = subprocess.CalledProcessError(
        1,
        ["qdbus6"],
        output="",
        stderr="",
    )

    with (
        patch(
            "dynamic_wallpaper.plasma.shutil.which",
            return_value="/usr/bin/qdbus6",
        ),
        patch(
            "dynamic_wallpaper.plasma.subprocess.run",
            side_effect=error,
        ),
    ):
        with pytest.raises(
            PlasmaError,
            match="Plasma rejected the wallpaper update",
        ):
            set_wallpaper(tmp_path / "wallpaper.png")
