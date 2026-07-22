"""KDE Plasma wallpaper integration."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


class PlasmaError(RuntimeError):
    """Raised when Plasma cannot update the wallpaper."""


def set_wallpaper(image_path: Path) -> None:
    qdbus = shutil.which("qdbus6")

    if qdbus is None:
        raise PlasmaError("qdbus6 was not found")

    wallpaper_uri = image_path.resolve().as_uri()
    encoded_uri = json.dumps(wallpaper_uri)

    script = f"""
const allDesktops = desktops();

for (let index = 0; index < allDesktops.length; index++) {{
    const desktop = allDesktops[index];

    desktop.wallpaperPlugin = "org.kde.image";
    desktop.currentConfigGroup = [
        "Wallpaper",
        "org.kde.image",
        "General"
    ];

    desktop.writeConfig("Image", {encoded_uri});
}}
""".strip()

    try:
        subprocess.run(
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
