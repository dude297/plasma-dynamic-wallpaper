"""Tests for KDE Plasma wallpaper integration."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from dynamic_wallpaper.plasma import PlasmaError, set_wallpaper


def _response(
    image: Path,
    *,
    updated_screens: tuple[int, ...] = (0,),
    active_images: tuple[tuple[int, str], ...] | None = None,
) -> subprocess.CompletedProcess[str]:
    uri = image.resolve().as_uri()
    updated = [
        {"id": 113 + screen, "screen": screen, "image": uri}
        for screen in updated_screens
    ]
    active = (
        [
            {"id": 113 + screen, "screen": screen, "image": active_uri}
            for screen, active_uri in active_images
        ]
        if active_images is not None
        else list(updated)
    )
    return subprocess.CompletedProcess(
        args=["qdbus6"],
        returncode=0,
        stdout=json.dumps({"updated": updated, "active": active}) + "\n",
        stderr="",
    )


def test_set_wallpaper_requires_existing_image(tmp_path: Path) -> None:
    with pytest.raises(PlasmaError, match="Wallpaper image was not found"):
        set_wallpaper(tmp_path / "missing.png")


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
            "dynamic_wallpaper.plasma._create_render_alias", return_value=image
        ),
        patch("dynamic_wallpaper.plasma._prune_render_aliases") as prune,
        patch(
            "dynamic_wallpaper.plasma.subprocess.run",
            return_value=_response(image),
        ) as run,
    ):
        set_wallpaper(image)

    args = run.call_args.args[0]
    assert args[:4] == [
        "/usr/bin/qdbus6",
        "org.kde.plasmashell",
        "/PlasmaShell",
        "org.kde.PlasmaShell.evaluateScript",
    ]
    assert run.call_args.kwargs == {
        "check": True,
        "capture_output": True,
        "text": True,
        "timeout": 15,
    }
    script = args[4]
    assert "const activeDesktops" in script
    assert "desktop.screen >= 0" in script
    assert "const targetDesktops" in script
    assert "activeDesktops.length === 0" in script
    assert "targetDesktops.length === 0" in script
    assert "index < targetDesktops.length" in script
    assert "const updated = [];" in script
    assert "const active = [];" in script
    assert "print(JSON.stringify({updated, active}));" in script
    assert 'desktop.wallpaperPlugin = "org.kde.image";' in script
    assert 'desktop.writeConfig("Image",' in script
    assert "desktop.reloadConfig();" in script
    assert image.resolve().as_uri() in script
    assert "%22day%22" in script
    prune.assert_called_once_with(
        image.parent,
        protected_uris={image.resolve().as_uri()},
        keep=16,
    )


def test_set_wallpaper_accepts_multiple_verified_desktops(
    tmp_path: Path,
) -> None:
    image = tmp_path / "wallpaper.png"
    image.touch()
    with (
        patch("dynamic_wallpaper.plasma.shutil.which", return_value="qdbus6"),
        patch(
            "dynamic_wallpaper.plasma._create_render_alias", return_value=image
        ),
        patch(
            "dynamic_wallpaper.plasma.subprocess.run",
            return_value=_response(image, updated_screens=(0, 1)),
        ),
    ):
        set_wallpaper(image)


def test_set_wallpaper_targets_requested_screens(tmp_path: Path) -> None:
    image = tmp_path / "wallpaper.png"
    image.touch()
    with (
        patch("dynamic_wallpaper.plasma.shutil.which", return_value="qdbus6"),
        patch(
            "dynamic_wallpaper.plasma._create_render_alias", return_value=image
        ),
        patch(
            "dynamic_wallpaper.plasma.subprocess.run",
            return_value=_response(image, updated_screens=(1,)),
        ) as run,
    ):
        set_wallpaper(image, (1,))
    script = run.call_args.args[0][4]
    assert "const requestedScreens = [1];" in script
    assert "requestedScreens.includes(desktop.screen)" in script
    assert "index < targetDesktops.length" in script


def test_set_wallpaper_rejects_empty_output(tmp_path: Path) -> None:
    image = tmp_path / "wallpaper.png"
    image.touch()
    response = subprocess.CompletedProcess(["qdbus6"], 0, "", "")
    with (
        patch("dynamic_wallpaper.plasma.shutil.which", return_value="qdbus6"),
        patch(
            "dynamic_wallpaper.plasma._create_render_alias", return_value=image
        ),
        patch(
            "dynamic_wallpaper.plasma.subprocess.run", return_value=response
        ),
        pytest.raises(PlasmaError, match="invalid verification response"),
    ):
        set_wallpaper(image)


def test_set_wallpaper_rejects_mismatched_readback(tmp_path: Path) -> None:
    image = tmp_path / "wallpaper.png"
    image.touch()
    payload = {
        "updated": [{"id": 113, "screen": 0, "image": "file:///tmp/old.png"}],
        "active": [{"id": 113, "screen": 0, "image": "file:///tmp/old.png"}],
    }
    response = subprocess.CompletedProcess(
        ["qdbus6"], 0, json.dumps(payload), ""
    )
    with (
        patch("dynamic_wallpaper.plasma.shutil.which", return_value="qdbus6"),
        patch(
            "dynamic_wallpaper.plasma._create_render_alias", return_value=image
        ),
        patch(
            "dynamic_wallpaper.plasma.subprocess.run", return_value=response
        ),
        pytest.raises(PlasmaError, match="did not retain"),
    ):
        set_wallpaper(image)


def test_set_wallpaper_warns_about_missing_requested_screen(
    tmp_path: Path,
) -> None:
    image = tmp_path / "wallpaper.png"
    image.touch()
    with (
        patch("dynamic_wallpaper.plasma.shutil.which", return_value="qdbus6"),
        patch(
            "dynamic_wallpaper.plasma._create_render_alias", return_value=image
        ),
        patch(
            "dynamic_wallpaper.plasma.subprocess.run",
            return_value=_response(image, updated_screens=(0,)),
        ),
        patch("dynamic_wallpaper.plasma.logger.warning") as warning,
    ):
        set_wallpaper(image, (0, 1))

    warning.assert_called_once()
    assert "temporarily unavailable" in warning.call_args.args[0]
    assert warning.call_args.args[1] == "1"


@pytest.mark.parametrize(
    ("stderr", "stdout", "message"),
    [
        ("Plasma is unavailable\n", "ignored", "Plasma is unavailable"),
        ("", "evaluation failed\n", "evaluation failed"),
        ("", "", "Plasma rejected the wallpaper update"),
    ],
)
def test_set_wallpaper_reports_command_failure(
    tmp_path: Path, stderr: str, stdout: str, message: str
) -> None:
    image = tmp_path / "wallpaper.png"
    image.touch()
    error = subprocess.CalledProcessError(
        1, ["qdbus6"], output=stdout, stderr=stderr
    )
    with (
        patch("dynamic_wallpaper.plasma.shutil.which", return_value="qdbus6"),
        patch("dynamic_wallpaper.plasma.subprocess.run", side_effect=error),
        pytest.raises(PlasmaError, match=message),
    ):
        set_wallpaper(image)


def test_create_render_alias_is_unique_and_sortable(tmp_path: Path) -> None:
    from dynamic_wallpaper.plasma import _create_render_alias

    image = tmp_path / "wallpaper.png"
    image.write_bytes(b"wallpaper")
    first = _create_render_alias(image)
    second = _create_render_alias(image)
    assert first != second
    assert first.name < second.name
    assert first.read_bytes() == b"wallpaper"
    assert first.stat().st_ino == image.stat().st_ino


def test_create_render_alias_falls_back_to_copy(tmp_path: Path) -> None:
    from dynamic_wallpaper.plasma import _create_render_alias

    image = tmp_path / "wallpaper.png"
    image.write_bytes(b"wallpaper")
    with patch.object(Path, "hardlink_to", side_effect=OSError("no link")):
        alias = _create_render_alias(image)
    assert alias.read_bytes() == b"wallpaper"


def test_prune_render_aliases_preserves_active_uri(tmp_path: Path) -> None:
    from dynamic_wallpaper.plasma import _prune_render_aliases

    render_dir = tmp_path / ".plasma-render"
    render_dir.mkdir()
    aliases = []
    for index in range(6):
        alias = render_dir / f"frame-{index:02d}.png"
        alias.touch()
        aliases.append(alias)

    active = aliases[0]
    _prune_render_aliases(
        render_dir,
        protected_uris={active.resolve().as_uri()},
        keep=2,
    )
    remaining = set(render_dir.iterdir())
    assert active in remaining
    assert aliases[-1] in remaining
    assert aliases[-2] in remaining
    assert len(remaining) == 3


def test_verify_wallpaper_response_returns_updated_and_active(
    tmp_path: Path,
) -> None:
    from dynamic_wallpaper.plasma import _verify_wallpaper_response

    uri = (tmp_path / "wallpaper.png").resolve().as_uri()
    old_uri = (tmp_path / "old.png").resolve().as_uri()
    output = json.dumps(
        {
            "updated": [{"id": 1, "screen": 0, "image": uri}],
            "active": [
                {"id": 1, "screen": 0, "image": uri},
                {"id": 2, "screen": 1, "image": old_uri},
            ],
        }
    )
    updated, active, missing = _verify_wallpaper_response(output, uri, (0,))
    assert [record["id"] for record in updated] == [1]
    assert active == {uri, old_uri}
    assert missing == set()


def test_wallpaper_is_configured_accepts_existing_render_alias(
    tmp_path: Path,
) -> None:
    from dynamic_wallpaper.plasma import wallpaper_is_configured

    frame = tmp_path / "frame-3.png"
    frame.touch()
    render_dir = tmp_path / ".plasma-render"
    render_dir.mkdir()
    alias = render_dir / "frame-3-0001-token.png"
    alias.touch()
    response = subprocess.CompletedProcess(
        ["qdbus6"],
        0,
        json.dumps(
            [{"id": 113, "screen": 0, "image": alias.resolve().as_uri()}]
        ),
        "",
    )
    with (
        patch("dynamic_wallpaper.plasma.shutil.which", return_value="qdbus6"),
        patch(
            "dynamic_wallpaper.plasma.subprocess.run", return_value=response
        ),
    ):
        assert wallpaper_is_configured(frame)


def test_wallpaper_is_configured_rejects_missing_alias(tmp_path: Path) -> None:
    from dynamic_wallpaper.plasma import wallpaper_is_configured

    frame = tmp_path / "frame-3.png"
    frame.touch()
    missing = tmp_path / ".plasma-render" / "frame-3-missing.png"
    response = subprocess.CompletedProcess(
        ["qdbus6"],
        0,
        json.dumps(
            [{"id": 113, "screen": 0, "image": missing.resolve().as_uri()}]
        ),
        "",
    )
    with (
        patch("dynamic_wallpaper.plasma.shutil.which", return_value="qdbus6"),
        patch(
            "dynamic_wallpaper.plasma.subprocess.run", return_value=response
        ),
    ):
        assert not wallpaper_is_configured(frame)


def test_set_wallpaper_reports_timeout(tmp_path: Path) -> None:
    image = tmp_path / "wallpaper.png"
    image.touch()
    with (
        patch("dynamic_wallpaper.plasma.shutil.which", return_value="qdbus6"),
        patch(
            "dynamic_wallpaper.plasma.subprocess.run",
            side_effect=subprocess.TimeoutExpired(["qdbus6"], 15),
        ),
        pytest.raises(PlasmaError, match="timed out"),
    ):
        set_wallpaper(image)


def test_verify_wallpaper_response_reports_temporarily_missing_screen(
    tmp_path: Path,
) -> None:
    from dynamic_wallpaper.plasma import _verify_wallpaper_response

    uri = (tmp_path / "wallpaper.png").resolve().as_uri()
    output = json.dumps(
        {
            "updated": [{"id": 1, "screen": 0, "image": uri}],
            "active": [
                {"id": 1, "screen": 0, "image": uri},
                {"id": 2, "screen": -1, "image": "file:///tmp/old.png"},
            ],
        }
    )

    updated, active, missing = _verify_wallpaper_response(output, uri, (0, 1))

    assert [record["screen"] for record in updated] == [0]
    assert active == {uri, "file:///tmp/old.png"}
    assert missing == {1}


def test_wallpaper_query_ignores_inactive_desktops(tmp_path: Path) -> None:
    from dynamic_wallpaper.plasma import wallpaper_is_configured

    frame = tmp_path / "frame-3.png"
    frame.touch()
    response = subprocess.CompletedProcess(
        ["qdbus6"],
        0,
        json.dumps(
            [{"id": 113, "screen": 0, "image": frame.resolve().as_uri()}]
        ),
        "",
    )
    with (
        patch("dynamic_wallpaper.plasma.shutil.which", return_value="qdbus6"),
        patch(
            "dynamic_wallpaper.plasma.subprocess.run", return_value=response
        ) as run,
    ):
        assert wallpaper_is_configured(frame)

    script = run.call_args.args[0][4]
    assert "desktop.screen >= 0" in script
    assert "? activeDesktops" in script


def test_wait_for_plasma_returns_when_active_desktop_is_ready() -> None:
    from dynamic_wallpaper.plasma import wait_for_plasma

    records = [{"id": 113, "screen": 0, "image": "file:///wallpaper.png"}]
    with (
        patch(
            "dynamic_wallpaper.plasma.plasma_desktops", return_value=records
        ),
        patch("dynamic_wallpaper.plasma.sleep") as sleep,
    ):
        assert wait_for_plasma((0,)) == records

    sleep.assert_not_called()


def test_wait_for_plasma_retries_transient_failures() -> None:
    from dynamic_wallpaper.plasma import wait_for_plasma

    records = [{"id": 113, "screen": 0, "image": "file:///wallpaper.png"}]
    with (
        patch(
            "dynamic_wallpaper.plasma.plasma_desktops",
            side_effect=[PlasmaError("service unavailable"), [], records],
        ) as query,
        patch("dynamic_wallpaper.plasma.monotonic", return_value=0.0),
        patch("dynamic_wallpaper.plasma.sleep") as sleep,
    ):
        assert wait_for_plasma(timeout=10, interval=0.5) == records

    assert query.call_count == 3
    assert sleep.call_count == 2
    sleep.assert_called_with(0.5)


def test_wait_for_plasma_times_out_with_last_error() -> None:
    from dynamic_wallpaper.plasma import wait_for_plasma

    with (
        patch(
            "dynamic_wallpaper.plasma.plasma_desktops",
            side_effect=PlasmaError("D-Bus name is unavailable"),
        ),
        patch("dynamic_wallpaper.plasma.monotonic", side_effect=[0.0, 5.0]),
        patch("dynamic_wallpaper.plasma.sleep") as sleep,
        pytest.raises(
            PlasmaError,
            match=(
                "did not become ready within 5 seconds: "
                "D-Bus name is unavailable"
            ),
        ),
    ):
        wait_for_plasma(timeout=5)

    sleep.assert_not_called()


@pytest.mark.parametrize(
    ("timeout", "interval", "message"),
    [
        (0.0, 1.0, "timeout must be positive"),
        (5.0, 0.0, "interval must be positive"),
    ],
)
def test_wait_for_plasma_rejects_invalid_timing(
    timeout: float,
    interval: float,
    message: str,
) -> None:
    from dynamic_wallpaper.plasma import wait_for_plasma

    with pytest.raises(ValueError, match=message):
        wait_for_plasma(timeout=timeout, interval=interval)
