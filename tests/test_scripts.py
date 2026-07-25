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
