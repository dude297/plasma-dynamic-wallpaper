"""Wallpaper catalog discovery and safe installation."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen


DEFAULT_CATALOG_URL = (
    "https://raw.githubusercontent.com/dude297/"
    "plasma-dynamic-wallpaper-library/main/catalog.json"
)
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_MAX_CATALOG_BYTES = 2 * 1024 * 1024
_MAX_WALLPAPER_BYTES = 1024 * 1024 * 1024


class LibraryError(RuntimeError):
    """Raised when a wallpaper-library operation cannot be completed."""


@dataclass(frozen=True)
class WallpaperEntry:
    """A validated wallpaper catalog entry."""

    wallpaper_id: str
    name: str
    author: str
    description: str
    download_url: str
    sha256: str
    filename: str


def library_root() -> Path:
    """Return the per-user wallpaper-library directory."""
    data_home = Path(
        os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
    )
    return data_home / "dynamic-wallpaper" / "wallpapers"


def catalog_url() -> str:
    """Return the configured catalog URL."""
    return os.environ.get("PDW_CATALOG_URL", DEFAULT_CATALOG_URL)


def _read_url(url: str, *, max_bytes: int) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme not in {"https", "file"}:
        raise LibraryError(
            "catalog and wallpaper URLs must use HTTPS or file://"
        )

    request = Request(url, headers={"User-Agent": "plasma-dynamic-wallpaper"})
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310
            data = response.read(max_bytes + 1)
    except OSError as exc:
        raise LibraryError(f"could not download {url}: {exc}") from exc

    if len(data) > max_bytes:
        raise LibraryError(
            f"download exceeded the {max_bytes}-byte safety limit"
        )
    return data


def _require_string(raw: dict[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise LibraryError(f"catalog entry has invalid or missing {key!r}")
    return value.strip()


def _parse_entry(raw: Any) -> WallpaperEntry:
    if not isinstance(raw, dict):
        raise LibraryError("catalog entries must be JSON objects")

    wallpaper_id = _require_string(raw, "id")
    if not _ID_PATTERN.fullmatch(wallpaper_id):
        raise LibraryError(f"invalid wallpaper id: {wallpaper_id!r}")

    download_url = _require_string(raw, "download_url")
    parsed_url = urlparse(download_url)
    if parsed_url.scheme not in {"https", "file"}:
        raise LibraryError(f"wallpaper {wallpaper_id!r} uses an unsafe URL")

    sha256 = _require_string(raw, "sha256").casefold()
    if not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise LibraryError(f"wallpaper {wallpaper_id!r} has an invalid sha256")

    filename = raw.get("filename", f"{wallpaper_id}.heic")
    if not isinstance(filename, str) or Path(filename).name != filename:
        raise LibraryError(
            f"wallpaper {wallpaper_id!r} has an invalid filename"
        )
    if Path(filename).suffix.casefold() != ".heic":
        raise LibraryError(
            f"wallpaper {wallpaper_id!r} filename must end in .heic"
        )

    return WallpaperEntry(
        wallpaper_id=wallpaper_id,
        name=_require_string(raw, "name"),
        author=str(raw.get("author", "Unknown")).strip() or "Unknown",
        description=str(raw.get("description", "")).strip(),
        download_url=download_url,
        sha256=sha256,
        filename=filename,
    )


def load_catalog(url: str | None = None) -> tuple[WallpaperEntry, ...]:
    """Download and validate a wallpaper catalog."""
    payload = _read_url(url or catalog_url(), max_bytes=_MAX_CATALOG_BYTES)
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LibraryError(f"catalog is not valid UTF-8 JSON: {exc}") from exc

    raw_entries = (
        decoded.get("wallpapers") if isinstance(decoded, dict) else None
    )
    if not isinstance(raw_entries, list):
        raise LibraryError("catalog must contain a 'wallpapers' array")

    entries = tuple(_parse_entry(raw) for raw in raw_entries)
    identifiers = [entry.wallpaper_id for entry in entries]
    if len(set(identifiers)) != len(identifiers):
        raise LibraryError("catalog contains duplicate wallpaper ids")
    return entries


def search_catalog(
    entries: tuple[WallpaperEntry, ...], term: str
) -> tuple[WallpaperEntry, ...]:
    """Return entries matching a case-insensitive search term."""
    needle = term.casefold().strip()
    if not needle:
        return entries
    return tuple(
        entry
        for entry in entries
        if needle
        in " ".join(
            (entry.wallpaper_id, entry.name, entry.author, entry.description)
        ).casefold()
    )


def find_entry(
    entries: tuple[WallpaperEntry, ...], wallpaper_id: str
) -> WallpaperEntry:
    """Find one catalog entry by exact id."""
    for entry in entries:
        if entry.wallpaper_id == wallpaper_id:
            return entry
    raise LibraryError(f"wallpaper not found in catalog: {wallpaper_id}")


def install_wallpaper(entry: WallpaperEntry, root: Path | None = None) -> Path:
    """Download, verify, and atomically install one HEIC wallpaper."""
    root = root or library_root()
    destination_dir = root / entry.wallpaper_id
    destination = destination_dir / entry.filename
    destination_dir.mkdir(parents=True, exist_ok=True)

    payload = _read_url(entry.download_url, max_bytes=_MAX_WALLPAPER_BYTES)
    digest = hashlib.sha256(payload).hexdigest()
    if digest != entry.sha256:
        raise LibraryError(
            f"checksum mismatch for {entry.wallpaper_id}: "
            f"expected {entry.sha256}, received {digest}"
        )

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination_dir,
            prefix=f".{entry.filename}.",
            delete=False,
        ) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            temp_path = Path(handle.name)
        temp_path.replace(destination)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

    return destination


def installed_wallpapers(root: Path | None = None) -> tuple[Path, ...]:
    """Return installed HEIC files in deterministic order."""
    root = root or library_root()
    if not root.is_dir():
        return ()
    return tuple(sorted(root.glob("*/*.heic")))


def remove_wallpaper(wallpaper_id: str, root: Path | None = None) -> Path:
    """Remove an installed wallpaper directory."""
    if not _ID_PATTERN.fullmatch(wallpaper_id):
        raise LibraryError(f"invalid wallpaper id: {wallpaper_id!r}")
    root = root or library_root()
    target = root / wallpaper_id
    if not target.is_dir():
        raise LibraryError(f"wallpaper is not installed: {wallpaper_id}")
    shutil.rmtree(target)
    return target
