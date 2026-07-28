"""Tests for the dynamic-wallpaper command-line interface."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from dynamic_wallpaper import cli
from dynamic_wallpaper.cache import CacheError
from dynamic_wallpaper.config import Config
from dynamic_wallpaper.metadata import MetadataError
from dynamic_wallpaper.plasma import PlasmaError
from dynamic_wallpaper.scheduler import ScheduleError
from dynamic_wallpaper.state import StateError


def test_package_version_uses_installed_metadata() -> None:
    with patch("dynamic_wallpaper.cli.version", return_value="1.2.3"):
        assert cli._package_version() == "1.2.3"


def test_package_version_has_source_fallback() -> None:
    with patch(
        "dynamic_wallpaper.cli.version",
        side_effect=cli.PackageNotFoundError,
    ):
        assert cli._package_version() == "0+unknown"


def test_parse_time_accepts_24_hour_time() -> None:
    with patch("dynamic_wallpaper.cli.datetime") as mocked_datetime:
        mocked_datetime.strptime.return_value = datetime(1900, 1, 1, 20, 45)
        mocked_datetime.now.return_value = datetime(2026, 7, 23, 9, 30, 10)

        parsed = cli._parse_time("20:45")

    assert parsed == datetime(2026, 7, 23, 20, 45)
    mocked_datetime.strptime.assert_called_once_with("20:45", "%H:%M")


def test_parse_time_rejects_invalid_format() -> None:
    with pytest.raises(
        argparse.ArgumentTypeError,
        match="24-hour HH:MM format",
    ):
        cli._parse_time("8pm")


def test_build_parser_exposes_expected_options() -> None:
    help_text = cli.build_parser().format_help()

    for option in (
        "--version",
        "--doctor",
        "--config",
        "--status",
        "--cache-status",
        "--rebuild-cache",
        "--inspect",
        "--schedule",
        "--extract",
        "--setup",
        "--setup-no-enable",
        "--library-list",
        "--library-installed",
        "--library-search TERM",
        "--library-install ID",
        "--library-remove ID",
        "--at HH:MM",
        "--dry-run",
        "--verbose",
        "--log-file PATH",
        "--force",
    ):
        assert option in help_text


def test_parser_rejects_multiple_primary_actions() -> None:
    parser = cli.build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["--status", "--schedule"])


def test_main_prints_active_configuration(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = Config(
        heic_file=Path("/wallpapers/Fuji.heic"),
        cache_dir=Path("/cache/Fuji"),
    )

    monkeypatch.setattr(sys, "argv", ["dynamic-wallpaper", "--config"])
    monkeypatch.setattr(cli, "load_config", Mock(return_value=config))
    monkeypatch.setattr(cli, "validate_config", Mock())
    monkeypatch.setattr(
        cli,
        "config_path",
        Mock(return_value="/config/dynamic-wallpaper/config"),
    )
    engine_type = Mock()
    monkeypatch.setattr(cli, "WallpaperEngine", engine_type)

    result = cli.main()

    assert result == 0
    assert capsys.readouterr().out == (
        "Configuration file: /config/dynamic-wallpaper/config\n"
        "Source HEIC: /wallpapers/Fuji.heic\n"
        "Cache directory: /cache/Fuji\n"
        "Target screens: all\n"
    )
    engine_type.assert_not_called()


def run_main_with_engine(
    monkeypatch: pytest.MonkeyPatch,
    arguments: list[str],
    engine: Mock,
) -> tuple[int, Mock]:
    config = Config(
        heic_file=SimpleNamespace(),
        cache_dir=SimpleNamespace(),
    )
    engine_type = Mock(return_value=engine)

    monkeypatch.setattr(sys, "argv", ["dynamic-wallpaper", *arguments])
    monkeypatch.setattr(cli, "load_config", Mock(return_value=config))
    monkeypatch.setattr(cli, "validate_config", Mock())
    monkeypatch.setattr(cli, "WallpaperEngine", engine_type)

    return cli.main(), engine_type


def test_main_runs_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["dynamic-wallpaper", "--doctor"])
    monkeypatch.setattr(
        cli,
        "run_diagnostics",
        Mock(return_value=(["[OK] Python: 3.14.4"], True)),
    )

    result = cli.main()

    assert result == 0
    assert capsys.readouterr().out == "[OK] Python: 3.14.4\n"


def test_main_returns_failure_for_unhealthy_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["dynamic-wallpaper", "--doctor"])
    monkeypatch.setattr(
        cli,
        "run_diagnostics",
        Mock(return_value=(["[FAIL] qdbus6: not found in PATH"], False)),
    )

    result = cli.main()

    assert result == 1
    assert capsys.readouterr().out == ("[FAIL] qdbus6: not found in PATH\n")


def test_main_prints_status(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    engine = Mock()
    engine.status.return_value = [
        "Last wallpaper: /cache/frame-2.png",
        "Last frame: 2",
    ]

    result, _ = run_main_with_engine(monkeypatch, ["--status"], engine)

    assert result == 0
    assert capsys.readouterr().out == (
        "Last wallpaper: /cache/frame-2.png\nLast frame: 2\n"
    )
    engine.status.assert_called_once_with()
    engine.apply.assert_not_called()


def test_main_prints_cache_status(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    engine = Mock()
    engine.cache_status.return_value = [
        "Cache directory: /cache/Fuji",
        "Cached frames: 7",
        "Cache current: yes",
    ]

    result, _ = run_main_with_engine(monkeypatch, ["--cache-status"], engine)

    assert result == 0
    assert capsys.readouterr().out == (
        "Cache directory: /cache/Fuji\nCached frames: 7\nCache current: yes\n"
    )
    engine.cache_status.assert_called_once_with()
    engine.apply.assert_not_called()


def test_main_rebuilds_cache(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    engine = Mock()
    engine.rebuild_cache.return_value = "Rebuilt 7 frame(s) in /cache/Fuji"

    result, _ = run_main_with_engine(monkeypatch, ["--rebuild-cache"], engine)

    assert result == 0
    captured = capsys.readouterr()
    assert captured.out == "Rebuilt 7 frame(s) in /cache/Fuji\n"
    assert captured.err == "Rebuilding cache in namespace()...\n"
    engine.rebuild_cache.assert_called_once_with()
    engine.apply.assert_not_called()


def test_main_inspects_metadata(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    engine = Mock()
    engine.inspect.return_value = '{"ti": []}'

    result, engine_type = run_main_with_engine(
        monkeypatch,
        ["--inspect"],
        engine,
    )

    assert result == 0
    assert capsys.readouterr().out == '{"ti": []}\n'
    engine_type.assert_called_once()
    engine.inspect.assert_called_once_with()
    engine.schedule.assert_not_called()
    engine.apply.assert_not_called()


def test_main_prints_schedule_lines(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    engine = Mock()
    engine.schedule.return_value = [
        "00:00 -> frame 0",
        "12:00 -> frame 1",
    ]

    result, _ = run_main_with_engine(
        monkeypatch,
        ["--schedule"],
        engine,
    )

    assert result == 0
    assert capsys.readouterr().out == ("00:00 -> frame 0\n12:00 -> frame 1\n")
    engine.schedule.assert_called_once_with()
    engine.apply.assert_not_called()


def test_main_extracts_frames(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    engine = Mock()
    engine.extract.return_value = "Prepared 7 frame(s) in /cache"

    result, _ = run_main_with_engine(
        monkeypatch,
        ["--extract"],
        engine,
    )

    assert result == 0
    assert capsys.readouterr().out == "Prepared 7 frame(s) in /cache\n"
    engine.extract.assert_called_once_with()
    engine.apply.assert_not_called()


def test_main_applies_selected_time_and_flags(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    engine = Mock()
    engine.apply.return_value = [
        "Would apply frame 2/6: /cache/frame-2.png",
        "Time 20:00; schedule entry 20:00",
    ]

    result, _ = run_main_with_engine(
        monkeypatch,
        ["--at", "20:00", "--dry-run", "--force"],
        engine,
    )

    assert result == 0
    output = capsys.readouterr().out
    assert "Would apply frame 2/6" in output
    selected_time = engine.apply.call_args.args[0]
    assert selected_time.hour == 20
    assert selected_time.minute == 0
    assert engine.apply.call_args.kwargs == {
        "dry_run": True,
        "force": True,
    }


def test_main_uses_current_time_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = Mock()
    engine.apply.return_value = []
    current_time = datetime(2026, 7, 23, 14, 15)

    monkeypatch.setattr(sys, "argv", ["dynamic-wallpaper"])
    monkeypatch.setattr(cli, "load_config", Mock())
    monkeypatch.setattr(cli, "validate_config", Mock())
    monkeypatch.setattr(cli, "WallpaperEngine", Mock(return_value=engine))

    with patch("dynamic_wallpaper.cli.datetime") as mocked_datetime:
        mocked_datetime.now.return_value = current_time
        result = cli.main()

    assert result == 0
    engine.apply.assert_called_once_with(
        current_time,
        dry_run=False,
        force=False,
    )


@pytest.mark.parametrize(
    "error",
    [
        CacheError("cache failed"),
        FileNotFoundError("missing file"),
        MetadataError("metadata failed"),
        PlasmaError("plasma failed"),
        ScheduleError("schedule failed"),
        StateError("state failed"),
        ValueError("configuration failed"),
    ],
)
def test_main_reports_expected_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    error: Exception,
) -> None:
    engine = Mock()
    engine.apply.side_effect = error

    result, _ = run_main_with_engine(monkeypatch, [], engine)

    captured = capsys.readouterr()
    assert result == 1
    assert captured.out == ""
    assert captured.err == f"dynamic-wallpaper: {error}\n"


def test_main_handles_interrupted_rebuild(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    engine = Mock()
    engine.rebuild_cache.side_effect = KeyboardInterrupt

    result, _ = run_main_with_engine(monkeypatch, ["--rebuild-cache"], engine)

    captured = capsys.readouterr()
    assert result == 130
    assert captured.out == ""
    assert "Rebuilding cache" in captured.err
    assert "operation interrupted; existing cache preserved" in captured.err


def test_main_configures_verbose_file_logging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = Mock()
    engine.apply.return_value = []
    configure = Mock()
    monkeypatch.setattr(cli, "configure_logging", configure)

    result, _ = run_main_with_engine(
        monkeypatch,
        ["--verbose", "--log-file", "/tmp/dynamic.log"],
        engine,
    )

    assert result == 0
    configure.assert_called_once_with(
        verbose=True,
        log_file=Path("/tmp/dynamic.log"),
    )


def test_main_reports_log_file_setup_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["dynamic-wallpaper", "--log-file", "/bad/log"],
    )
    monkeypatch.setattr(
        cli,
        "configure_logging",
        Mock(side_effect=PermissionError("permission denied")),
    )

    assert cli.main() == 1
    assert (
        "could not open log file: permission denied" in capsys.readouterr().err
    )
