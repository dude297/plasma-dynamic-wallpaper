"""Logging configuration for dynamic-wallpaper."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

LOGGER_NAME = "dynamic_wallpaper"


class _MillisecondsFormatter(logging.Formatter):
    """Format timestamps with millisecond precision."""

    default_msec_format = "%s.%03d"


def configure_logging(
    *, verbose: bool = False, log_file: Path | None = None
) -> None:
    """Configure package logging for one CLI invocation.

    Normal scheduled runs remain quiet unless an error occurs. ``--verbose``
    enables debug output on stderr, while ``--log-file`` records informational
    diagnostics and timing data in a persistent file.
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    formatter = _MillisecondsFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.DEBUG if verbose else logging.CRITICAL + 1)
    console.setFormatter(formatter)
    logger.addHandler(console)

    if log_file is not None:
        resolved = log_file.expanduser()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(resolved, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a child logger within the application namespace."""
    return logging.getLogger(f"{LOGGER_NAME}.{name}")
