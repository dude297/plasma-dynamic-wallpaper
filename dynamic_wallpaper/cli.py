"""Command-line interface for dynamic-wallpaper."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from .cache import CacheError, prepare_frames
from .config import load_config
from .metadata import MetadataError, decode_h24
from .plasma import PlasmaError, set_wallpaper
from .scheduler import ScheduleError, format_schedule, select_frame
from .state import StateError, is_current, save_state


def _json_default(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"type": "bytes", "hex": value.hex()}

    if isinstance(value, datetime):
        return value.isoformat()

    raise TypeError(f"Cannot serialize {type(value).__name__}")


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

    try:
        config = load_config()

        if not config.heic_file.is_file():
            raise FileNotFoundError(
                f"HEIC wallpaper not found: {config.heic_file}"
            )

        metadata = decode_h24(config.heic_file)

        if args.inspect:
            print(
                json.dumps(
                    metadata,
                    indent=2,
                    default=_json_default,
                )
            )
            return 0

        if args.schedule:
            for line in format_schedule(metadata):
                print(line)

            appearance = metadata.get("ap")

            if isinstance(appearance, dict):
                print()
                print(
                    "Appearance alternatives: "
                    f"light={appearance.get('l')}, "
                    f"dark={appearance.get('d')}"
                )

            return 0

        frames = prepare_frames(
            config.heic_file,
            config.cache_dir,
        )

        if args.extract:
            print(
                f"Prepared {len(frames)} frame(s) "
                f"in {config.cache_dir}"
            )
            return 0

        selected_time = args.at or datetime.now()

        index, wallpaper, entry = select_frame(
            frames,
            metadata,
            selected_time,
        )

        state_file = config.cache_dir.parent / "state.json"

        if args.dry_run:
            action = "Would keep" if is_current(
                state_file,
                wallpaper,
            ) else "Would apply"

            print(
                f"{action} frame {index}/{len(frames) - 1}: "
                f"{wallpaper}"
            )
        elif not args.force and is_current(state_file, wallpaper):
            print(
                f"Skipped frame {index}/{len(frames) - 1}: "
                "already applied"
            )
        else:
            set_wallpaper(wallpaper)
            save_state(state_file, wallpaper, index)

            print(
                f"Applied frame {index}/{len(frames) - 1}: "
                f"{wallpaper}"
            )

        start_hour, start_minute = divmod(entry.minutes, 60)

        print(
            f"Time {selected_time:%H:%M}; schedule entry "
            f"{start_hour:02d}:{start_minute:02d}"
        )

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
