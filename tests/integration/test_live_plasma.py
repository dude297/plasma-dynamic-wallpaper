"""Opt-in tests that exercise a live KDE Plasma session."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from dynamic_wallpaper.plasma import set_wallpaper

pytestmark = pytest.mark.integration

_RUN_LIVE = os.environ.get("PDW_RUN_LIVE_PLASMA_TESTS") == "1"


@pytest.fixture(autouse=True)
def require_live_plasma() -> None:
    """Skip unless the caller explicitly enables destructive desktop tests."""
    if not _RUN_LIVE:
        pytest.skip("set PDW_RUN_LIVE_PLASMA_TESTS=1 inside a Plasma session")

    if shutil.which("qdbus6") is None:
        pytest.skip("qdbus6 is not installed")


@pytest.fixture
def original_wallpapers() -> list[dict[str, object]]:
    """Capture current wallpaper configuration and restore it after the test."""
    records = _read_wallpapers()
    if not records:
        pytest.skip("Plasma reported no desktop containments")

    yield records

    _restore_wallpapers(records)


def test_set_wallpaper_in_live_plasma_session(
    tmp_path: Path,
    original_wallpapers: list[dict[str, object]],
) -> None:
    """Apply an image through qdbus and verify every desktop read-back."""
    image = tmp_path / "integration-wallpaper.png"
    image.write_bytes(
        bytes.fromhex(
            "89504e470d0a1a0a0000000d494844520000000100000001"
            "08060000001f15c4890000000d49444154789c63606060f8"
            "0f0001040100fca73d2d0000000049454e44ae426082"
        )
    )

    set_wallpaper(image)

    records = _read_wallpapers()
    assert len(records) == len(original_wallpapers)

    for record in records:
        uri = record.get("image")
        assert isinstance(uri, str)
        assert "/.plasma-render/integration-wallpaper-" in uri
        assert uri.endswith(".png")


def _evaluate_plasma(script: str) -> str:
    completed = subprocess.run(
        [
            "qdbus6",
            "org.kde.plasmashell",
            "/PlasmaShell",
            "org.kde.PlasmaShell.evaluateScript",
            script,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def _read_wallpapers() -> list[dict[str, object]]:
    output = _evaluate_plasma(
        """
for (const desktop of desktops()) {
    desktop.currentConfigGroup = [
        "Wallpaper",
        "org.kde.image",
        "General"
    ];
    print(JSON.stringify({
        id: desktop.id,
        screen: desktop.screen,
        image: desktop.readConfig("Image", "")
    }));
}
""".strip()
    )
    return [json.loads(line) for line in output.splitlines() if line.strip()]


def _restore_wallpapers(records: list[dict[str, object]]) -> None:
    encoded = json.dumps(records)
    _evaluate_plasma(
        f"""
const saved = {encoded};
const allDesktops = desktops();

for (const desktop of allDesktops) {{
    const match = saved.find((item) => item.id === desktop.id);
    if (!match) {{
        continue;
    }}

    desktop.wallpaperPlugin = "org.kde.image";
    desktop.currentConfigGroup = [
        "Wallpaper",
        "org.kde.image",
        "General"
    ];
    desktop.writeConfig("Image", match.image);
    desktop.reloadConfig();
}}
""".strip()
    )
