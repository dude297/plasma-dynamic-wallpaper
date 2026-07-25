"""KDE Plasma wallpaper integration."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


class PlasmaError(RuntimeError):
    """Raised when Plasma cannot update the wallpaper."""


def set_wallpaper(image_path: Path) -> None:
    """Apply *image_path* to every Plasma desktop and verify the write."""
    if not image_path.is_file():
        raise PlasmaError(f"Wallpaper image was not found: {image_path}")

    qdbus = shutil.which("qdbus6")

    if qdbus is None:
        raise PlasmaError("qdbus6 was not found")

    wallpaper_uri = image_path.resolve().as_uri()
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

    _verify_wallpaper_response(completed.stdout, wallpaper_uri)


def _verify_wallpaper_response(output: str, expected_uri: str) -> None:
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
