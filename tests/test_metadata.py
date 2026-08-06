"""Tests for Apple Dynamic Desktop metadata decoding."""

from __future__ import annotations

import base64
import json
import plistlib
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from dynamic_wallpaper.metadata import (
    MetadataError,
    _run_exiftool,
    decode_h24,
    extract_h24_value,
)

HEIC_FILE = Path("/tmp/wallpaper.heic")


def completed_process(stdout: str, stderr: str = "") -> Mock:
    """Return a subprocess result with the fields used by metadata.py."""
    return Mock(stdout=stdout, stderr=stderr)


def encode_plist(value: object) -> str:
    """Encode a value as the Base64 Apple binary plist stored in h24."""
    binary_plist = plistlib.dumps(value, fmt=plistlib.FMT_BINARY)
    return base64.b64encode(binary_plist).decode("ascii")


def test_run_exiftool_requests_h24_metadata() -> None:
    payload = [{"XMP-apple_desktop:H24": "encoded"}]

    with patch(
        "dynamic_wallpaper.metadata.subprocess.run",
        return_value=completed_process(json.dumps(payload)),
    ) as run:
        result = _run_exiftool(HEIC_FILE)

    assert result == payload
    run.assert_called_once_with(
        [
            "exiftool",
            "-j",
            "-a",
            "-G1",
            "-XMP-apple_desktop:H24",
            str(HEIC_FILE),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_run_exiftool_reports_missing_executable() -> None:
    with (
        patch(
            "dynamic_wallpaper.metadata.subprocess.run",
            side_effect=FileNotFoundError,
        ),
        pytest.raises(MetadataError, match="exiftool is required"),
    ):
        _run_exiftool(HEIC_FILE)


def test_run_exiftool_reports_command_failure_stderr() -> None:
    error = subprocess.CalledProcessError(
        returncode=1,
        cmd=["exiftool"],
        stderr="cannot read HEIC",
    )

    with (
        patch(
            "dynamic_wallpaper.metadata.subprocess.run",
            side_effect=error,
        ),
        pytest.raises(MetadataError, match="cannot read HEIC"),
    ):
        _run_exiftool(HEIC_FILE)


def test_run_exiftool_uses_fallback_command_failure_message() -> None:
    error = subprocess.CalledProcessError(
        returncode=1,
        cmd=["exiftool"],
        stderr="",
    )

    with (
        patch(
            "dynamic_wallpaper.metadata.subprocess.run",
            side_effect=error,
        ),
        pytest.raises(MetadataError, match="exiftool failed"),
    ):
        _run_exiftool(HEIC_FILE)


def test_run_exiftool_rejects_invalid_json() -> None:
    with (
        patch(
            "dynamic_wallpaper.metadata.subprocess.run",
            return_value=completed_process("not-json"),
        ),
        pytest.raises(MetadataError, match="exiftool JSON output"),
    ):
        _run_exiftool(HEIC_FILE)


def test_run_exiftool_rejects_non_list_response() -> None:
    with (
        patch(
            "dynamic_wallpaper.metadata.subprocess.run",
            return_value=completed_process('{"H24": "encoded"}'),
        ),
        pytest.raises(MetadataError, match="Unexpected exiftool"),
    ):
        _run_exiftool(HEIC_FILE)


def test_extract_h24_value_accepts_normalized_key_and_trims_value() -> None:
    payload = [{"XMP-apple_desktop:H24": "  encoded-value  "}]

    with patch(
        "dynamic_wallpaper.metadata._run_exiftool",
        return_value=payload,
    ):
        assert extract_h24_value(HEIC_FILE) == "encoded-value"


def test_extract_h24_value_matches_key_case_insensitively() -> None:
    payload = [{"xmp-APPLE_DESKTOP:h24": "encoded-value"}]

    with patch(
        "dynamic_wallpaper.metadata._run_exiftool",
        return_value=payload,
    ):
        assert extract_h24_value(HEIC_FILE) == "encoded-value"


def test_extract_h24_value_rejects_empty_payload() -> None:
    with (
        patch(
            "dynamic_wallpaper.metadata._run_exiftool",
            return_value=[],
        ),
        pytest.raises(MetadataError, match="No metadata was returned"),
    ):
        extract_h24_value(HEIC_FILE)


def test_extract_h24_value_rejects_missing_h24() -> None:
    payload = [{"SourceFile": str(HEIC_FILE)}]

    with (
        patch(
            "dynamic_wallpaper.metadata._run_exiftool",
            return_value=payload,
        ),
        pytest.raises(MetadataError, match="does not contain"),
    ):
        extract_h24_value(HEIC_FILE)


def test_extract_h24_value_rejects_non_string_h24() -> None:
    payload = [{"XMP-apple_desktop:H24": 123}]

    with (
        patch(
            "dynamic_wallpaper.metadata._run_exiftool",
            return_value=payload,
        ),
        pytest.raises(MetadataError, match="does not contain"),
    ):
        extract_h24_value(HEIC_FILE)


def test_decode_h24_returns_embedded_property_list() -> None:
    metadata = {
        "ti": [
            {"t": 0.0, "i": 0},
            {"t": 0.5, "i": 1},
        ],
        "ap": {"l": 0, "d": 1},
    }

    with patch(
        "dynamic_wallpaper.metadata.extract_h24_value",
        return_value=encode_plist(metadata),
    ):
        assert decode_h24(HEIC_FILE) == metadata


def test_decode_h24_rejects_invalid_base64() -> None:
    with (
        patch(
            "dynamic_wallpaper.metadata.extract_h24_value",
            return_value="not valid base64!",
        ),
        pytest.raises(MetadataError, match="not valid Base64"),
    ):
        decode_h24(HEIC_FILE)


def test_decode_h24_rejects_non_binary_plist() -> None:
    encoded = base64.b64encode(b"plain text").decode("ascii")

    with (
        patch(
            "dynamic_wallpaper.metadata.extract_h24_value",
            return_value=encoded,
        ),
        pytest.raises(MetadataError, match="not an Apple binary plist"),
    ):
        decode_h24(HEIC_FILE)


def test_decode_h24_rejects_malformed_binary_plist() -> None:
    encoded = base64.b64encode(b"bplist00malformed").decode("ascii")

    with (
        patch(
            "dynamic_wallpaper.metadata.extract_h24_value",
            return_value=encoded,
        ),
        pytest.raises(MetadataError, match="Could not parse"),
    ):
        decode_h24(HEIC_FILE)


def test_load_h24_metadata_reuses_valid_disk_cache(tmp_path: Path) -> None:
    from dynamic_wallpaper.metadata import load_h24_metadata

    heic_file = tmp_path / "wallpaper.heic"
    cache_dir = tmp_path / "cache"
    heic_file.write_bytes(b"heic")
    metadata = {"ti": [{"t": 0.0, "i": 0}]}

    with patch(
        "dynamic_wallpaper.metadata.decode_h24",
        return_value=metadata,
    ) as decode:
        assert load_h24_metadata(heic_file, cache_dir) == metadata
        assert load_h24_metadata(heic_file, cache_dir) == metadata

    decode.assert_called_once_with(heic_file)


def test_load_h24_metadata_invalidates_when_source_changes(
    tmp_path: Path,
) -> None:
    from dynamic_wallpaper.metadata import load_h24_metadata

    heic_file = tmp_path / "wallpaper.heic"
    cache_dir = tmp_path / "cache"
    heic_file.write_bytes(b"first")

    with patch(
        "dynamic_wallpaper.metadata.decode_h24",
        side_effect=[{"generation": 1}, {"generation": 2}],
    ) as decode:
        assert load_h24_metadata(heic_file, cache_dir) == {"generation": 1}
        heic_file.write_bytes(b"second-generation")
        assert load_h24_metadata(heic_file, cache_dir) == {"generation": 2}

    assert decode.call_count == 2


def test_load_h24_metadata_recovers_from_corrupt_cache(
    tmp_path: Path,
) -> None:
    from dynamic_wallpaper.metadata import (
        _source_fingerprint,
        load_h24_metadata,
    )

    heic_file = tmp_path / "wallpaper.heic"
    cache_dir = tmp_path / "cache"
    heic_file.write_bytes(b"heic")
    cache_dir.mkdir()
    (cache_dir / ".metadata.plist").write_bytes(b"not-a-plist")
    (cache_dir / ".metadata-source").write_text(
        _source_fingerprint(heic_file),
        encoding="utf-8",
    )

    with patch(
        "dynamic_wallpaper.metadata.decode_h24",
        return_value={"fresh": True},
    ) as decode:
        assert load_h24_metadata(heic_file, cache_dir) == {"fresh": True}

    decode.assert_called_once_with(heic_file)
