"""KDE Plasma wallpaper integration."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from time import perf_counter, time_ns
from urllib.parse import unquote, urlparse
from uuid import uuid4

from .logging import get_logger


logger = get_logger("plasma")
_RENDER_ALIAS_LIMIT = 16
_QDBUS_TIMEOUT_SECONDS = 15


class PlasmaError(RuntimeError):
    """Raised when Plasma cannot update the wallpaper."""


def set_wallpaper(
    image_path: Path, screen_ids: tuple[int, ...] | None = None
) -> None:
    """Apply *image_path* to selected Plasma desktops and verify the write.

    A unique alias gives each application a fresh file URI, avoiding stale
    renderer caches. Alias cleanup occurs only after Plasma confirms the new
    configuration and never removes a file still referenced by any desktop.
    """
    if not image_path.is_file():
        raise PlasmaError(f"Wallpaper image was not found: {image_path}")

    qdbus = shutil.which("qdbus6")
    if qdbus is None:
        raise PlasmaError("qdbus6 was not found")

    render_path = _create_render_alias(image_path)
    wallpaper_uri = render_path.resolve().as_uri()
    encoded_uri = json.dumps(wallpaper_uri)
    encoded_screens = json.dumps(
        list(screen_ids) if screen_ids is not None else None
    )

    script = f"""
const allDesktops = desktops();
const requestedScreens = {encoded_screens};
const targetDesktops = requestedScreens === null
    ? allDesktops
    : allDesktops.filter(desktop => requestedScreens.includes(desktop.screen));

if (allDesktops.length === 0) {{
    throw new Error("Plasma reported no desktop containments");
}}

if (targetDesktops.length === 0) {{
    throw new Error("Plasma found no desktops matching the requested screens");
}}

const updated = [];
for (let index = 0; index < targetDesktops.length; index++) {{
    const desktop = targetDesktops[index];
    desktop.wallpaperPlugin = "org.kde.image";
    desktop.currentConfigGroup = [
        "Wallpaper",
        "org.kde.image",
        "General"
    ];
    desktop.writeConfig("Image", {encoded_uri});
    desktop.reloadConfig();
    updated.push({{
        id: desktop.id,
        screen: desktop.screen,
        image: desktop.readConfig("Image", "")
    }});
}}

const active = [];
for (let index = 0; index < allDesktops.length; index++) {{
    const desktop = allDesktops[index];
    desktop.currentConfigGroup = [
        "Wallpaper",
        "org.kde.image",
        "General"
    ];
    active.push({{
        id: desktop.id,
        screen: desktop.screen,
        image: desktop.readConfig("Image", "")
    }});
}}

print(JSON.stringify({{updated, active}}));
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
            timeout=_QDBUS_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise PlasmaError("Plasma wallpaper update timed out") from exc
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or exc.stdout.strip()
        raise PlasmaError(
            message or "Plasma rejected the wallpaper update"
        ) from exc

    elapsed_ms = (perf_counter() - started) * 1000
    logger.debug("Raw Plasma verification response: %r", completed.stdout)
    updated, active_uris = _verify_wallpaper_response(
        completed.stdout,
        wallpaper_uri,
        screen_ids,
    )
    _prune_render_aliases(
        render_path.parent,
        protected_uris=active_uris,
        keep=_RENDER_ALIAS_LIMIT,
    )
    logger.info(
        "Plasma verified %d desktop(s) in %.1f ms",
        len(updated),
        elapsed_ms,
    )


def wallpaper_is_configured(
    image_path: Path, screen_ids: tuple[int, ...] | None = None
) -> bool:
    """Return whether selected desktops reference a usable alias of a frame."""
    qdbus = shutil.which("qdbus6")
    if qdbus is None:
        raise PlasmaError("qdbus6 was not found")

    encoded_screens = json.dumps(
        list(screen_ids) if screen_ids is not None else None
    )
    script = f"""
const requestedScreens = {encoded_screens};
const selected = requestedScreens === null
    ? desktops()
    : desktops().filter(desktop => requestedScreens.includes(desktop.screen));
const result = [];
for (let index = 0; index < selected.length; index++) {{
    const desktop = selected[index];
    desktop.currentConfigGroup = [
        "Wallpaper",
        "org.kde.image",
        "General"
    ];
    result.push({{
        id: desktop.id,
        screen: desktop.screen,
        image: desktop.readConfig("Image", "")
    }});
}}
print(JSON.stringify(result));
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
            timeout=_QDBUS_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise PlasmaError("Plasma wallpaper query timed out") from exc
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or exc.stdout.strip()
        raise PlasmaError(
            message or "Could not query the configured Plasma wallpaper"
        ) from exc

    try:
        records = json.loads(completed.stdout.strip())
    except json.JSONDecodeError as exc:
        raise PlasmaError(
            "Plasma returned an invalid wallpaper query response"
        ) from exc
    if not isinstance(records, list) or not records:
        return False

    expected = image_path.resolve()
    for record in records:
        if not isinstance(record, dict):
            return False
        configured = _path_from_file_uri(record.get("image"))
        if configured is None or not configured.is_file():
            return False
        resolved = configured.resolve()
        if resolved == expected:
            continue
        if not (
            resolved.parent.name == ".plasma-render"
            and resolved.parent.parent == expected.parent
            and resolved.name.startswith(expected.stem + "-")
            and resolved.suffix == expected.suffix
        ):
            return False

    return True


def _create_render_alias(image_path: Path) -> Path:
    """Create a unique alias so Plasma receives a fresh URI every time."""
    render_dir = image_path.parent / ".plasma-render"
    render_dir.mkdir(parents=True, exist_ok=True)
    alias = render_dir / (
        f"{image_path.stem}-{time_ns():020d}-{uuid4().hex}{image_path.suffix}"
    )

    try:
        alias.hardlink_to(image_path)
    except OSError:
        shutil.copy2(image_path, alias)

    logger.debug("Created Plasma render alias: %s", alias)
    return alias


def _path_from_file_uri(uri: object) -> Path | None:
    if not isinstance(uri, str):
        return None
    parsed = urlparse(uri)
    if parsed.scheme != "file" or parsed.netloc not in {"", "localhost"}:
        return None
    return Path(unquote(parsed.path))


def _prune_render_aliases(
    render_dir: Path,
    *,
    protected_uris: set[str],
    keep: int,
) -> None:
    """Prune inactive aliases while preserving every active Plasma URI."""
    protected_paths = {
        path.resolve()
        for uri in protected_uris
        if (path := _path_from_file_uri(uri)) is not None
    }
    aliases = sorted(
        (path for path in render_dir.iterdir() if path.is_file()),
        key=lambda path: path.name,
        reverse=True,
    )
    inactive = [
        path for path in aliases if path.resolve() not in protected_paths
    ]

    for stale in inactive[keep:]:
        try:
            stale.unlink()
        except OSError:
            logger.debug(
                "Could not remove stale Plasma render alias: %s",
                stale,
            )


def _verification_records(
    value: object, field: str
) -> list[dict[str, object]]:
    if not isinstance(value, list) or not value:
        raise PlasmaError(f"Plasma did not report any {field} desktops")
    if not all(isinstance(record, dict) for record in value):
        raise PlasmaError(
            "Plasma returned an invalid wallpaper verification record"
        )
    return value


def _verify_wallpaper_response(
    output: str,
    expected_uri: str,
    expected_screens: tuple[int, ...] | None = None,
) -> tuple[list[dict[str, object]], set[str]]:
    """Verify updated desktops and return every active wallpaper URI."""
    try:
        payload = json.loads(output.strip())
    except json.JSONDecodeError as exc:
        raise PlasmaError(
            f"Plasma returned an invalid verification response: {output.strip()}"
        ) from exc

    if not isinstance(payload, dict):
        raise PlasmaError("Plasma returned an invalid verification response")

    updated = _verification_records(payload.get("updated"), "updated")
    active = _verification_records(payload.get("active"), "active")

    if expected_screens is not None:
        reported_screens = {record.get("screen") for record in updated}
        missing_screens = set(expected_screens) - reported_screens
        if missing_screens:
            missing = ", ".join(
                str(value) for value in sorted(missing_screens)
            )
            raise PlasmaError(
                "Plasma did not report requested screen(s): " + missing
            )

    mismatches = [
        record for record in updated if record.get("image") != expected_uri
    ]
    if mismatches:
        details = ", ".join(
            f"desktop {record.get('id', '?')}: {record.get('image', '')!r}"
            for record in mismatches
        )
        raise PlasmaError(
            "Plasma did not retain the requested wallpaper: " + details
        )

    active_uris = {
        image
        for record in active
        if isinstance((image := record.get("image")), str) and image
    }
    return updated, active_uris
