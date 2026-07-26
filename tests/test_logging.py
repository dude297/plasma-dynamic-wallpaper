"""Tests for application logging configuration."""

from __future__ import annotations

import logging
from pathlib import Path

from dynamic_wallpaper.logging import (
    LOGGER_NAME,
    configure_logging,
    get_logger,
)


def test_default_logging_keeps_logs_off_stderr(capsys) -> None:
    configure_logging()

    logger = get_logger("test")
    logger.info("quiet info")
    logger.warning("visible warning")

    captured = capsys.readouterr()
    assert "quiet info" not in captured.err
    assert "visible warning" not in captured.err


def test_verbose_logging_writes_debug_to_stderr(capsys) -> None:
    configure_logging(verbose=True)

    get_logger("test").debug("debug details")

    assert (
        "DEBUG dynamic_wallpaper.test: debug details"
        in capsys.readouterr().err
    )


def test_log_file_creates_parent_and_records_info(tmp_path: Path) -> None:
    log_file = tmp_path / "nested" / "run.log"
    configure_logging(log_file=log_file)

    get_logger("test").info("selected frame 2")
    for handler in logging.getLogger(LOGGER_NAME).handlers:
        handler.flush()

    assert log_file.is_file()
    assert (
        "INFO dynamic_wallpaper.test: selected frame 2" in log_file.read_text()
    )


def test_reconfigure_replaces_existing_handlers(tmp_path: Path) -> None:
    configure_logging(log_file=tmp_path / "first.log")
    configure_logging(log_file=tmp_path / "second.log")

    logger = logging.getLogger(LOGGER_NAME)

    assert len(logger.handlers) == 2
