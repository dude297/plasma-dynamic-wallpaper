"""Apple Dynamic Desktop metadata decoding."""

from __future__ import annotations

import base64
import json
import plistlib
import subprocess
import tempfile
from pathlib import Path
from typing import Any

_METADATA_CACHE_VERSION = 1


class MetadataError(RuntimeError):
    """Raised when Dynamic Desktop metadata cannot be decoded."""


def _run_exiftool(heic_file: Path) -> list[dict[str, Any]]:
    command = [
        "exiftool",
        "-j",
        "-a",
        "-G1",
        "-XMP-apple_desktop:H24",
        str(heic_file),
    ]

    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        raise MetadataError("exiftool timed out") from exc
    except FileNotFoundError as exc:
        raise MetadataError("exiftool is required but was not found") from exc
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or "exiftool failed"
        raise MetadataError(message) from exc

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise MetadataError("Could not decode exiftool JSON output") from exc

    if not isinstance(payload, list):
        raise MetadataError("Unexpected exiftool response")

    return payload


def extract_h24_value(heic_file: Path) -> str:
    payload = _run_exiftool(heic_file)

    if not payload:
        raise MetadataError("No metadata was returned")

    metadata = payload[0]

    for key, value in metadata.items():
        normalized = key.lower().replace("_", "")

        if normalized.endswith(":h24") and isinstance(value, str):
            return value.strip()

    raise MetadataError(
        "This HEIC does not contain apple_desktop:h24 metadata"
    )


def decode_h24(heic_file: Path) -> Any:
    encoded = extract_h24_value(heic_file)

    try:
        binary_plist = base64.b64decode(
            encoded,
            validate=True,
        )
    except ValueError as exc:
        raise MetadataError("apple_desktop:h24 is not valid Base64") from exc

    if not binary_plist.startswith(b"bplist00"):
        raise MetadataError("Decoded h24 data is not an Apple binary plist")

    try:
        return plistlib.loads(binary_plist)
    except plistlib.InvalidFileException as exc:
        raise MetadataError(
            "Could not parse the embedded Apple property list"
        ) from exc


def _metadata_cache_paths(cache_dir: Path) -> tuple[Path, Path]:
    return cache_dir / ".metadata.plist", cache_dir / ".metadata-source"


def _source_fingerprint(heic_file: Path) -> str:
    stat = heic_file.stat()
    return f"{_METADATA_CACHE_VERSION}:{stat.st_mtime_ns}:{stat.st_size}"


def load_h24_metadata(heic_file: Path, cache_dir: Path) -> Any:
    """Load decoded h24 metadata from disk when the source is unchanged."""
    cache_file, marker_file = _metadata_cache_paths(cache_dir)
    fingerprint = _source_fingerprint(heic_file)

    try:
        if (
            cache_file.is_file()
            and marker_file.read_text(encoding="utf-8").strip() == fingerprint
        ):
            return plistlib.loads(cache_file.read_bytes())
    except (OSError, plistlib.InvalidFileException):
        pass

    metadata = decode_h24(heic_file)
    cache_dir.mkdir(parents=True, exist_ok=True)

    temporary_path: Path | None = None
    try:
        payload = plistlib.dumps(metadata, fmt=plistlib.FMT_BINARY)
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=cache_dir,
            prefix=".metadata-",
            delete=False,
        ) as temporary:
            temporary.write(payload)
            temporary_path = Path(temporary.name)
        temporary_path.replace(cache_file)
        marker_file.write_text(fingerprint + "\n", encoding="utf-8")
    except (OSError, TypeError, OverflowError):
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    return metadata
