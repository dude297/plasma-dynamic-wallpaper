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
            "dynamic_wallpaper.plasma._create_render_alias",
            return_value=image,
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
            "dynamic_wallpaper.plasma._create_render_alias",
            return_value=image,
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


def test_verify_wallpaper_response_returns_verified_records(
    tmp_path: Path,
) -> None:
    image = tmp_path / "wallpaper.png"
    uri = image.resolve().as_uri()
    output = "\n".join(
        [
            json.dumps({"id": 1, "screen": 0, "image": uri}),
            json.dumps({"id": 2, "screen": 1, "image": uri}),
        ]
    )

    from dynamic_wallpaper.plasma import _verify_wallpaper_response

    records = _verify_wallpaper_response(output, uri)

    assert [record["id"] for record in records] == [1, 2]


def test_create_render_alias_uses_unique_hard_link(tmp_path: Path) -> None:
    from dynamic_wallpaper.plasma import _create_render_alias

    image = tmp_path / "wallpaper.png"
    image.write_bytes(b"wallpaper")

    first = _create_render_alias(image)
    second = _create_render_alias(image)

    assert first != second
    assert first.parent == tmp_path / ".plasma-render"
    assert first.read_bytes() == b"wallpaper"
    assert second.read_bytes() == b"wallpaper"
    assert first.stat().st_ino == image.stat().st_ino


def test_create_render_alias_falls_back_to_copy(tmp_path: Path) -> None:
    from dynamic_wallpaper.plasma import _create_render_alias

    image = tmp_path / "wallpaper.png"
    image.write_bytes(b"wallpaper")

    with patch.object(Path, "hardlink_to", side_effect=OSError("no link")):
        alias = _create_render_alias(image)

    assert alias.read_bytes() == b"wallpaper"


def test_create_render_alias_prunes_old_entries(tmp_path: Path) -> None:
    from dynamic_wallpaper.plasma import _create_render_alias

    image = tmp_path / "wallpaper.png"
    image.write_bytes(b"wallpaper")

    for _ in range(12):
        _create_render_alias(image)

    aliases = list((tmp_path / ".plasma-render").iterdir())
    assert len(aliases) == 8


def test_set_wallpaper_targets_requested_screens(tmp_path: Path) -> None:
    image = tmp_path / "wallpaper.png"
    image.touch()
    uri = image.resolve().as_uri()
    response = subprocess.CompletedProcess(
        args=["qdbus6"],
        returncode=0,
        stdout=json.dumps({"id": 114, "screen": 1, "image": uri}) + "\n",
        stderr="",
    )

    with (
        patch("dynamic_wallpaper.plasma.shutil.which", return_value="qdbus6"),
        patch(
            "dynamic_wallpaper.plasma._create_render_alias",
            return_value=image,
        ),
        patch(
            "dynamic_wallpaper.plasma.subprocess.run",
            return_value=response,
        ) as run,
    ):
        set_wallpaper(image, (1,))

    script = run.call_args.args[0][4]
    assert "const requestedScreens = [1];" in script
    assert "requestedScreens.includes(desktop.screen)" in script
    assert "targetDesktops" in script


def test_verify_wallpaper_response_rejects_missing_requested_screen(
    tmp_path: Path,
) -> None:
    from dynamic_wallpaper.plasma import _verify_wallpaper_response

    uri = (tmp_path / "wallpaper.png").resolve().as_uri()
    output = json.dumps({"id": 113, "screen": 0, "image": uri})

    with pytest.raises(PlasmaError, match="requested screen.*1"):
        _verify_wallpaper_response(output, uri, (0, 1))
