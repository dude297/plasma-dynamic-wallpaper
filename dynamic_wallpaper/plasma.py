"""KDE Plasma wallpaper integration."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from .logging import get_logger


logger = get_logger("plasma")


class PlasmaError(RuntimeError):
    """Raised when Plasma cannot update the wallpaper."""


def set_wallpaper(image_path: Path) -> None:
    """Apply *image_path* to every Plasma desktop and verify the write.

    Plasma can retain the requested configuration while its renderer continues
    showing a stale or default image.  A unique alias gives each application a
    fresh file URI, invalidating that renderer cache without restarting Plasma.
    """
    if not image_path.is_file():
        raise PlasmaError(f"Wallpaper image was not found: {image_path}")

    qdbus = shutil.which("qdbus6")

    if qdbus is None:
        raise PlasmaError("qdbus6 was not found")

    render_path = _create_render_alias(image_path)
    wallpaper_uri = render_path.resolve().as_uri()
    encoded_uri = json.dumps(wallpaper_uri)

    # Plasma can persist the new Image value without repainting the desktop.
    # reloadConfig() asks each containment to refresh immediately, while the
    # explicit read-back lets us distinguish a rejected/stale configuration
    # write from a renderer problem inside plasmashell.
    script = f"""
const allDesktops = desktops();

if (allDesktops.length === 0) {{
    throw new Error("Plasma reported no desktop containments");
}}

for (let index = 0; index < allDesktops.length; index++) {{
    const desktop = allDesktops[index];

    desktop.wallpaperPlugin = "org.kde.image";
    desktop.currentConfigGroup = [
        "Wallpaper",
        "org.kde.image",
        "General"
    ];

    desktop.writeConfig("Image", {encoded_uri});
    desktop.reloadConfig();

    const appliedImage = desktop.readConfig("Image", "");
    print(JSON.stringify({{
        id: desktop.id,
        screen: desktop.screen,
        image: appliedImage
    }}));
}}
""".strip()

    logger.info("Requesting Plasma wallpaper update: %s", wallpaper_uri)
    logger.debug("Plasma evaluateScript payload:\n%s", script)
    started = perf_counter()

    try:
        completed = subprocess.run(
            [
                qdbus,
                "org.kde.plasmashell",
                "/PlasmaShell",
                "org.kde.PlasmaShell.evaluateScript",
                script,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or exc.stdout.strip()
        raise PlasmaError(
            message or "Plasma rejected the wallpaper update"
        ) from exc

    elapsed_ms = (perf_counter() - started) * 1000
    logger.debug("Raw Plasma verification response: %r", completed.stdout)
    records = _verify_wallpaper_response(completed.stdout, wallpaper_uri)
    logger.info(
        "Plasma verified %d desktop(s) in %.1f ms",
        len(records),
        elapsed_ms,
    )


def _create_render_alias(image_path: Path) -> Path:
    """Create a unique alias so Plasma receives a fresh URI every time."""
    render_dir = image_path.parent / ".plasma-render"
    render_dir.mkdir(parents=True, exist_ok=True)

    alias = render_dir / (
        f"{image_path.stem}-{uuid4().hex}{image_path.suffix}"
    )

    try:
        alias.hardlink_to(image_path)
    except OSError:
        shutil.copy2(image_path, alias)

    _prune_render_aliases(render_dir, keep=8)
    logger.debug("Created Plasma render alias: %s", alias)
    return alias


def _prune_render_aliases(render_dir: Path, *, keep: int) -> None:
    """Retain only the newest render aliases."""
    aliases = sorted(
        (path for path in render_dir.iterdir() if path.is_file()),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    )

    for stale in aliases[keep:]:
        try:
            stale.unlink()
        except OSError:
            logger.debug(
                "Could not remove stale Plasma render alias: %s",
                stale,
            )


def _verify_wallpaper_response(
    output: str, expected_uri: str
) -> list[dict[str, object]]:
    """Verify that every desktop reports the requested wallpaper URI."""
    records: list[dict[str, object]] = []

    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue

        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise PlasmaError(
                f"Plasma returned an invalid verification response: {line}"
            ) from exc

        if not isinstance(record, dict):
            raise PlasmaError(
                "Plasma returned an invalid wallpaper verification record"
            )

        records.append(record)

    if not records:
        raise PlasmaError("Plasma did not report any updated desktops")

    mismatches = [
        record for record in records if record.get("image") != expected_uri
    ]
    if mismatches:
        details = ", ".join(
            f"desktop {record.get('id', '?')}: {record.get('image', '')!r}"
            for record in mismatches
        )
        raise PlasmaError(
            "Plasma did not retain the requested wallpaper: " + details
        )

    return records
