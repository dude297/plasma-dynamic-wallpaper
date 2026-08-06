from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("script", "expected"),
    [
        ("install.sh", "Install plasma-dynamic-wallpaper"),
        ("uninstall.sh", "Remove plasma-dynamic-wallpaper"),
    ],
)
def test_script_help(script: str, expected: str) -> None:
    result = subprocess.run(
        ["bash", str(ROOT / script), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert expected in result.stdout


@pytest.mark.parametrize("script", ["install.sh", "uninstall.sh"])
def test_script_rejects_unknown_option(script: str) -> None:
    result = subprocess.run(
        ["bash", str(ROOT / script), "--not-a-real-option"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "Unknown option" in result.stderr


def test_release_helper_reports_version() -> None:
    result = subprocess.run(
        ["python", str(ROOT / "scripts" / "release.py"), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Validate and build" in result.stdout
    assert "--native" in result.stdout


def test_debian_builder_rejects_unknown_option() -> None:
    result = subprocess.run(
        [
            "bash",
            str(ROOT / "packaging" / "debian" / "build-deb.sh"),
            "--unknown",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "Usage:" in result.stderr
