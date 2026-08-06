"""Tests for operational readiness diagnostics."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

from dynamic_wallpaper.config import Config
from dynamic_wallpaper.diagnostics import (
    DiagnosticResult,
    _cache_check,
    _command_check,
    _config_checks,
    _heic_check,
    _nearest_existing_parent,
    run_diagnostics,
)


def test_diagnostic_result_formats_status() -> None:
    assert DiagnosticResult("example", True, "ready").format() == (
        "[OK] example: ready"
    )
    assert DiagnosticResult("example", False, "broken").format() == (
        "[FAIL] example: broken"
    )


def test_command_check_reports_found_and_missing_commands() -> None:
    with patch(
        "dynamic_wallpaper.diagnostics.shutil.which",
        side_effect=["/usr/bin/tool", None],
    ):
        found = _command_check("tool")
        missing = _command_check("missing")

    assert found.ok is True
    assert found.detail == "/usr/bin/tool"
    assert missing.ok is False
    assert missing.detail == "not found in PATH"


def test_heic_check_reports_existing_and_missing_files(tmp_path: Path) -> None:
    wallpaper = tmp_path / "wallpaper.heic"
    config = Config(wallpaper, tmp_path / "cache")

    assert _heic_check(config).ok is False

    wallpaper.write_bytes(b"heic")

    assert _heic_check(config).ok is True


def test_cache_check_accepts_existing_writable_directory(
    tmp_path: Path,
) -> None:
    config = Config(tmp_path / "wallpaper.heic", tmp_path / "cache")
    config.cache_dir.mkdir()

    with patch("dynamic_wallpaper.diagnostics.os.access", return_value=True):
        result = _cache_check(config)

    assert result.ok is True
    assert result.detail.startswith("writable:")


def test_cache_check_accepts_creatable_directory(tmp_path: Path) -> None:
    cache_dir = tmp_path / "nested" / "cache"
    config = Config(tmp_path / "wallpaper.heic", cache_dir)

    with patch("dynamic_wallpaper.diagnostics.os.access", return_value=True):
        result = _cache_check(config)

    assert result.ok is True
    assert result.detail == f"can be created: {cache_dir}"


def test_cache_check_rejects_unwritable_parent(tmp_path: Path) -> None:
    cache_dir = tmp_path / "nested" / "cache"
    config = Config(tmp_path / "wallpaper.heic", cache_dir)

    with patch("dynamic_wallpaper.diagnostics.os.access", return_value=False):
        result = _cache_check(config)

    assert result.ok is False
    assert result.detail == f"cannot be created under: {tmp_path}"


def test_nearest_existing_parent_walks_up(tmp_path: Path) -> None:
    assert _nearest_existing_parent(tmp_path / "a" / "b") == tmp_path


def test_config_checks_reports_loading_error() -> None:
    with patch(
        "dynamic_wallpaper.diagnostics.load_config",
        side_effect=FileNotFoundError("missing config"),
    ):
        results = _config_checks()

    assert results == [
        DiagnosticResult("configuration", False, "missing config")
    ]


def test_config_checks_reports_config_and_paths(tmp_path: Path) -> None:
    wallpaper = tmp_path / "wallpaper.heic"
    wallpaper.write_bytes(b"heic")
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    config = Config(wallpaper, cache_dir)

    with (
        patch(
            "dynamic_wallpaper.diagnostics.load_config",
            return_value=config,
        ),
        patch("dynamic_wallpaper.diagnostics.validate_config"),
        patch("dynamic_wallpaper.diagnostics.os.access", return_value=True),
    ):
        results = _config_checks()

    assert [result.ok for result in results] == [True, True, True]


def test_run_diagnostics_returns_failure_when_any_check_fails() -> None:
    with (
        patch(
            "dynamic_wallpaper.diagnostics.shutil.which",
            return_value=None,
        ),
        patch(
            "dynamic_wallpaper.diagnostics._config_checks",
            return_value=[DiagnosticResult("configuration", True, "valid")],
        ),
        patch.object(sys, "version_info", (3, 14)),
        patch.object(sys, "version", "3.14.4 test"),
    ):
        lines, healthy = run_diagnostics()

    assert healthy is False
    assert lines[0] == "[OK] Python: 3.14.4"
    assert "[FAIL] exiftool: not found in PATH" in lines
