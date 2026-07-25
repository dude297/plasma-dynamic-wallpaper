"""Command-line interface for dynamic-wallpaper."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version

from .cache import CacheError
from .config import load_config, validate_config
from .diagnostics import run_diagnostics
from .engine import WallpaperEngine
from .metadata import MetadataError
from .plasma import PlasmaError
from .scheduler import ScheduleError
from .state import StateError


def _package_version() -> str:
    """Return the installed package version."""
    try:
        return version("plasma-dynamic-wallpaper")
    except PackageNotFoundError:
        return "0+unknown"


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.strptime(value, "%H:%M")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "time must use 24-hour HH:MM format"
        ) from exc

    now = datetime.now()

    return now.replace(
        hour=parsed.hour,
        minute=parsed.minute,
        second=0,
        microsecond=0,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dynamic-wallpaper",
        description="Use Apple Dynamic Desktop HEIC files on KDE Plasma.",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_package_version()}",
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="check configuration and runtime dependencies",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="show the last successfully applied wallpaper",
    )
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="print the decoded Apple metadata",
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="print the embedded 24-hour schedule",
    )
    parser.add_argument(
        "--extract",
        action="store_true",
        help="extract and cache frames without changing wallpaper",
    )
    parser.add_argument(
        "--at",
        metavar="HH:MM",
        type=_parse_time,
        help="test frame selection at a specific time",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show the selected frame without applying it",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="apply the wallpaper even if it is already current",
    )

    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.doctor:
        lines, healthy = run_diagnostics()
        for line in lines:
            print(line)
        return 0 if healthy else 1

    try:
        config = load_config()
        validate_config(config)
        engine = WallpaperEngine(config)

        if args.status:
            for line in engine.status():
                print(line)
            return 0

        if args.inspect:
            print(engine.inspect())
            return 0

        if args.schedule:
            for line in engine.schedule():
                print(line)
            return 0

        if args.extract:
            print(engine.extract())
            return 0

        selected_time = args.at or datetime.now()

        for line in engine.apply(
            selected_time,
            dry_run=args.dry_run,
            force=args.force,
        ):
            print(line)

        return 0

    except (
        CacheError,
        FileNotFoundError,
        MetadataError,
        PlasmaError,
        ScheduleError,
        StateError,
        ValueError,
    ) as exc:
        print(f"dynamic-wallpaper: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
