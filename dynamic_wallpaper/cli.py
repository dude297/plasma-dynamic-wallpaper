"""Command-line interface for dynamic-wallpaper."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .cache import CacheError
from .config import config_path, load_config, validate_config
from .diagnostics import run_diagnostics
from .engine import WallpaperEngine
from .installer import InstallError, install_user
from .library import (
    LibraryError,
    active_installed_id,
    activate_wallpaper,
    find_entry,
    install_local_wallpaper,
    installed_entries,
    install_wallpaper,
    installed_wallpapers,
    load_catalog,
    remove_wallpaper,
    search_catalog,
)
from .logging import configure_logging, get_logger
from .metadata import MetadataError
from .plasma import PlasmaError, wait_for_plasma
from .scheduler import ScheduleError
from .state import StateError
from .watchdog import WatchdogError, watch_plasma


logger = get_logger("cli")


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
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument(
        "--doctor",
        action="store_true",
        help="check configuration and runtime dependencies",
    )
    actions.add_argument(
        "--config",
        action="store_true",
        help="show the active configuration and resolved paths",
    )
    actions.add_argument(
        "--status",
        action="store_true",
        help="show the last successfully applied wallpaper",
    )
    actions.add_argument(
        "--current",
        action="store_true",
        help="show the scheduled frame and active Plasma desktop state",
    )
    actions.add_argument(
        "--cache-status",
        action="store_true",
        help="show cache freshness and extracted frame count",
    )
    actions.add_argument(
        "--rebuild-cache",
        action="store_true",
        help="force extraction and replace cached frames",
    )
    actions.add_argument(
        "--inspect",
        action="store_true",
        help="print the decoded Apple metadata",
    )
    actions.add_argument(
        "--schedule",
        action="store_true",
        help="print the embedded 24-hour schedule",
    )
    actions.add_argument(
        "--extract",
        action="store_true",
        help="extract and cache frames without changing wallpaper",
    )
    actions.add_argument(
        "--startup",
        action="store_true",
        help="wait for Plasma readiness and apply the current frame",
    )
    actions.add_argument(
        "--watch",
        action="store_true",
        help="watch for Plasma restarts and suspend/resume recovery",
    )
    actions.add_argument(
        "--setup",
        action="store_true",
        help="install user configuration and enable the systemd timer",
    )
    actions.add_argument(
        "--setup-no-enable",
        action="store_true",
        help="install user configuration without enabling the timer",
    )
    actions.add_argument(
        "--library-list",
        action="store_true",
        help="list wallpapers available in the remote catalog",
    )
    actions.add_argument(
        "--library-installed",
        action="store_true",
        help="list wallpapers installed from the library",
    )
    actions.add_argument(
        "--library-search",
        metavar="TERM",
        help="search the remote wallpaper catalog",
    )
    actions.add_argument(
        "--library-install",
        metavar="ID",
        help="download and verify a wallpaper from the catalog",
    )
    actions.add_argument(
        "--library-remove",
        metavar="ID",
        help="remove a wallpaper installed from the library",
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
        "--verbose",
        action="store_true",
        help="show detailed diagnostic and timing information",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        metavar="PATH",
        help="write diagnostic logs to PATH",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="apply the wallpaper even if it is already current",
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=("list", "use", "install", "remove"),
        help="manage locally installed dynamic wallpapers",
    )
    parser.add_argument(
        "command_value",
        nargs="?",
        help="wallpaper ID or local HEIC file for the management command",
    )
    parser.add_argument(
        "--name",
        help="ID to use when installing a local HEIC wallpaper",
    )

    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        configure_logging(
            verbose=args.verbose,
            log_file=args.log_file,
            console_info=args.watch,
        )
    except OSError as exc:
        print(
            f"dynamic-wallpaper: could not open log file: {exc}",
            file=sys.stderr,
        )
        return 1

    logger.debug("CLI arguments: %s", vars(args))

    if args.doctor:
        lines, healthy = run_diagnostics()
        for line in lines:
            print(line)
        return 0 if healthy else 1

    try:
        if args.watch:
            watch_plasma()
            return 0

        if args.setup or args.setup_no_enable:
            for line in install_user(enable_timer=args.setup):
                print(line)
            return 0

        if args.command == "list":
            if args.command_value is not None:
                raise LibraryError("list does not accept an argument")
            entries = installed_entries()
            active_id: str | None = None
            try:
                active_id = active_installed_id(load_config().heic_file)
            except (FileNotFoundError, ValueError):
                pass
            if not entries:
                print("No managed wallpapers installed.")
                return 0
            for entry in entries:
                marker = "*" if entry.wallpaper_id == active_id else " "
                print(f"{marker} {entry.wallpaper_id}: {entry.heic_file}")
            return 0

        if args.command == "install":
            if args.command_value is None:
                raise LibraryError("install requires a local HEIC file")
            entry = install_local_wallpaper(
                Path(args.command_value), name=args.name
            )
            print(f"Installed {entry.wallpaper_id}: {entry.heic_file}")
            print(f"Use it with: dynamic-wallpaper use {entry.wallpaper_id}")
            return 0

        if args.command == "use":
            if args.command_value is None:
                raise LibraryError("use requires a wallpaper ID")
            entry = activate_wallpaper(args.command_value)
            print(f"Active wallpaper: {entry.wallpaper_id}")
            print(f"Source HEIC: {entry.heic_file}")
            print(f"Cache directory: {entry.cache_dir}")
            return 0

        if args.command == "remove":
            if args.command_value is None:
                raise LibraryError("remove requires a wallpaper ID")
            config = load_config()
            active_id = active_installed_id(config.heic_file)
            if active_id == args.command_value:
                raise LibraryError(
                    "cannot remove the active wallpaper; use another "
                    "wallpaper first"
                )
            removed = remove_wallpaper(args.command_value)
            print(f"Removed wallpaper: {removed}")
            return 0

        if args.command is None and args.name is not None:
            raise LibraryError("--name may only be used with install")

        if args.library_list or args.library_search is not None:
            entries = load_catalog()
            if args.library_search is not None:
                entries = search_catalog(entries, args.library_search)
            if not entries:
                print("No wallpapers found.")
                return 0
            for entry in entries:
                print(f"{entry.wallpaper_id}: {entry.name} — {entry.author}")
                if entry.description:
                    print(f"  {entry.description}")
            return 0

        if args.library_installed:
            installed = installed_wallpapers()
            if not installed:
                print("No library wallpapers installed.")
                return 0
            for path in installed:
                print(path)
            return 0

        if args.library_install is not None:
            entry = find_entry(load_catalog(), args.library_install)
            destination = install_wallpaper(entry)
            print(f"Installed {entry.name}: {destination}")
            print("To use it, set HEIC_FILE in your configuration to:")
            print(destination)
            return 0

        if args.library_remove is not None:
            removed = remove_wallpaper(args.library_remove)
            print(f"Removed wallpaper: {removed}")
            return 0

        config = load_config()
        validate_config(config)

        if args.config:
            print(f"Configuration file: {config_path()}")
            print(f"Source HEIC: {config.heic_file}")
            print(f"Cache directory: {config.cache_dir}")
            screens = (
                "all"
                if config.screen_ids is None
                else ", ".join(str(value) for value in config.screen_ids)
            )
            print(f"Target screens: {screens}")
            return 0

        engine = WallpaperEngine(config)

        if args.status:
            for line in engine.status():
                print(line)
            return 0

        if args.current:
            for line in engine.current(datetime.now()):
                print(line)
            return 0

        if args.cache_status:
            for line in engine.cache_status():
                print(line)
            return 0

        if args.rebuild_cache:
            print(
                f"Rebuilding cache in {config.cache_dir}...",
                file=sys.stderr,
                flush=True,
            )
            print(engine.rebuild_cache())
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

        if args.startup:
            logger.info("Waiting for Plasma desktop readiness")
            wait_for_plasma(config.screen_ids)

        selected_time = args.at or datetime.now()

        for line in engine.apply(
            selected_time,
            dry_run=args.dry_run,
            force=args.force or args.startup,
        ):
            print(line)

        return 0

    except KeyboardInterrupt:
        logger.warning("Operation interrupted by user")
        print(
            "dynamic-wallpaper: operation interrupted; existing cache preserved",
            file=sys.stderr,
        )
        return 130
    except (
        CacheError,
        FileNotFoundError,
        InstallError,
        LibraryError,
        MetadataError,
        PlasmaError,
        ScheduleError,
        StateError,
        ValueError,
        WatchdogError,
    ) as exc:
        logger.error("Command failed: %s", exc)
        print(f"dynamic-wallpaper: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
