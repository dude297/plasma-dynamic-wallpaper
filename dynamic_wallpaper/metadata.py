"""Apple Dynamic Desktop metadata decoding."""

from __future__ import annotations

import base64
import json
import plistlib
import subprocess
from pathlib import Path
from typing import Any


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
        )
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
