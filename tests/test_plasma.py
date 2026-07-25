"""Tests for KDE Plasma wallpaper integration."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from dynamic_wallpaper.plasma import PlasmaError, set_wallpaper


def _successful_response(image: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["qdbus6"],
        returncode=0,
        stdout=json.dumps(
            {
                "id": 113,
                "screen": 0,
                "image": image.resolve().as_uri(),
            }
        )
        + "\n",
        stderr="",
    )


def test_set_wallpaper_requires_existing_image(tmp_path: Path) -> None:
    image = tmp_path / "missing.png"

    with pytest.raises(PlasmaError, match="Wallpaper image was not found"):
        set_wallpaper(image)


def test_set_wallpaper_requires_qdbus6(tmp_path: Path) -> None:
    image = tmp_path / "wallpaper.png"
    image.touch()

    with (
        patch("dynamic_wallpaper.plasma.shutil.which", return_value=None),
        pytest.raises(PlasmaError, match="qdbus6 was not found"),
    ):
        set_wallpaper(image)


def test_set_wallpaper_invokes_plasma_shell(tmp_path: Path) -> None:
    image = tmp_path / 'wallpaper "day".png'
    image.touch()

    with (
        patch(
            "dynamic_wallpaper.plasma.shutil.which",
            return_value="/usr/bin/qdbus6",
        ),
        patch(
            "dynamic_wallpaper.plasma.subprocess.run",
            return_value=_successful_response(image),
        ) as run,
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
    assert "allDesktops.length === 0" in script
    assert 'desktop.wallpaperPlugin = "org.kde.image";' in script
    assert 'desktop.writeConfig("Image",' in script
    assert "desktop.reloadConfig();" in script
    assert 'desktop.readConfig("Image", "")' in script
    assert image.resolve().as_uri() in script
    assert "%22day%22" in script


def test_set_wallpaper_accepts_multiple_verified_desktops(
    tmp_path: Path,
) -> None:
    image = tmp_path / "wallpaper.png"
    image.touch()
    uri = image.resolve().as_uri()
    response = subprocess.CompletedProcess(
        args=["qdbus6"],
        returncode=0,
        stdout=(
            json.dumps({"id": 113, "screen": 0, "image": uri})
            + "\n"
            + json.dumps({"id": 114, "screen": 1, "image": uri})
            + "\n"
        ),
        stderr="",
    )

    with (
        patch(
            "dynamic_wallpaper.plasma.shutil.which",
            return_value="/usr/bin/qdbus6",
        ),
        patch(
            "dynamic_wallpaper.plasma.subprocess.run",
            return_value=response,
        ),
    ):
        set_wallpaper(image)


def test_set_wallpaper_rejects_missing_verification_output(
    tmp_path: Path,
) -> None:
    image = tmp_path / "wallpaper.png"
    image.touch()
    response = subprocess.CompletedProcess(
        args=["qdbus6"],
        returncode=0,
        stdout="",
        stderr="",
    )

    with (
        patch(
            "dynamic_wallpaper.plasma.shutil.which",
            return_value="/usr/bin/qdbus6",
        ),
        patch(
            "dynamic_wallpaper.plasma.subprocess.run",
            return_value=response,
        ),
        pytest.raises(
            PlasmaError,
            match="Plasma did not report any updated desktops",
        ),
    ):
        set_wallpaper(image)


def test_set_wallpaper_rejects_invalid_verification_output(
    tmp_path: Path,
) -> None:
    image = tmp_path / "wallpaper.png"
    image.touch()
    response = subprocess.CompletedProcess(
        args=["qdbus6"],
        returncode=0,
        stdout="not-json\n",
        stderr="",
    )

    with (
        patch(
            "dynamic_wallpaper.plasma.shutil.which",
            return_value="/usr/bin/qdbus6",
        ),
        patch(
            "dynamic_wallpaper.plasma.subprocess.run",
            return_value=response,
        ),
        pytest.raises(
            PlasmaError,
            match="invalid verification response",
        ),
    ):
        set_wallpaper(image)


def test_set_wallpaper_rejects_mismatched_readback(tmp_path: Path) -> None:
    image = tmp_path / "wallpaper.png"
    image.touch()
    response = subprocess.CompletedProcess(
        args=["qdbus6"],
        returncode=0,
        stdout=json.dumps(
            {
                "id": 113,
                "screen": 0,
                "image": "file:///tmp/old.png",
            }
        )
        + "\n",
        stderr="",
    )

    with (
        patch(
            "dynamic_wallpaper.plasma.shutil.which",
            return_value="/usr/bin/qdbus6",
        ),
        patch(
            "dynamic_wallpaper.plasma.subprocess.run",
            return_value=response,
        ),
        pytest.raises(
            PlasmaError,
            match="did not retain the requested wallpaper",
        ),
    ):
        set_wallpaper(image)


def test_set_wallpaper_uses_stderr_from_failed_command(
    tmp_path: Path,
) -> None:
    image = tmp_path / "wallpaper.png"
    image.touch()
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
        pytest.raises(PlasmaError, match="Plasma is unavailable"),
    ):
        set_wallpaper(image)


def test_set_wallpaper_falls_back_to_stdout_from_failed_command(
    tmp_path: Path,
) -> None:
    image = tmp_path / "wallpaper.png"
    image.touch()
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
        pytest.raises(PlasmaError, match="evaluation failed"),
    ):
        set_wallpaper(image)


def test_set_wallpaper_uses_generic_message_for_empty_failure(
    tmp_path: Path,
) -> None:
    image = tmp_path / "wallpaper.png"
    image.touch()
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
        pytest.raises(
            PlasmaError,
            match="Plasma rejected the wallpaper update",
        ),
    ):
        set_wallpaper(image)
