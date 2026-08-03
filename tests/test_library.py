"""Tests for wallpaper catalog and installation support."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from dynamic_wallpaper import library


def _catalog_payload(download_url: str, digest: str) -> bytes:
    return json.dumps(
        {
            "wallpapers": [
                {
                    "id": "fuji-test",
                    "name": "Fuji Test",
                    "author": "Test Author",
                    "description": "Test wallpaper",
                    "download_url": download_url,
                    "sha256": digest,
                    "filename": "fuji.heic",
                }
            ]
        }
    ).encode()


def test_load_catalog_validates_entries(
    tmp_path: Path,
) -> None:
    wallpaper = tmp_path / "fuji.heic"
    wallpaper.write_bytes(b"heic-test")
    digest = hashlib.sha256(wallpaper.read_bytes()).hexdigest()
    catalog = tmp_path / "catalog.json"
    catalog.write_bytes(_catalog_payload(wallpaper.as_uri(), digest))

    entries = library.load_catalog(catalog.as_uri())

    assert len(entries) == 1
    assert entries[0].wallpaper_id == "fuji-test"
    assert entries[0].filename == "fuji.heic"


def test_search_catalog_matches_metadata() -> None:
    entry = library.WallpaperEntry(
        wallpaper_id="fuji",
        name="Mount Fuji",
        author="Example",
        description="A mountain at sunrise",
        download_url="https://example.org/fuji.heic",
        sha256="0" * 64,
        filename="fuji.heic",
    )

    assert library.search_catalog((entry,), "SUNRISE") == (entry,)
    assert library.search_catalog((entry,), "ocean") == ()


def test_install_wallpaper_verifies_and_writes_atomically(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.heic"
    source.write_bytes(b"verified-heic")
    entry = library.WallpaperEntry(
        wallpaper_id="verified",
        name="Verified",
        author="Test",
        description="",
        download_url=source.as_uri(),
        sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        filename="verified.heic",
    )

    destination = library.install_wallpaper(entry, tmp_path / "library")

    assert destination.read_bytes() == b"verified-heic"
    assert destination == tmp_path / "library" / "verified" / "verified.heic"


def test_install_wallpaper_rejects_checksum_mismatch(tmp_path: Path) -> None:
    source = tmp_path / "source.heic"
    source.write_bytes(b"unexpected")
    entry = library.WallpaperEntry(
        wallpaper_id="bad",
        name="Bad",
        author="Test",
        description="",
        download_url=source.as_uri(),
        sha256="0" * 64,
        filename="bad.heic",
    )

    with pytest.raises(library.LibraryError, match="checksum mismatch"):
        library.install_wallpaper(entry, tmp_path / "library")


def test_remove_wallpaper(tmp_path: Path) -> None:
    installed = tmp_path / "library" / "fuji"
    installed.mkdir(parents=True)
    (installed / "fuji.heic").write_bytes(b"test")

    removed = library.remove_wallpaper("fuji", tmp_path / "library")

    assert removed == installed
    assert not installed.exists()


def test_install_local_wallpaper_and_find_installed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "Mountain View.heic"
    source.write_bytes(b"local-heic")
    root = tmp_path / "library"
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache-home"))

    entry = library.install_local_wallpaper(source, root=root)

    assert entry.wallpaper_id == "mountain-view"
    assert entry.heic_file.read_bytes() == b"local-heic"
    assert library.find_installed("mountain-view", root) == entry


def test_activate_wallpaper_updates_only_managed_config_values(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "fuji.heic"
    source.write_bytes(b"heic")
    root = tmp_path / "library"
    config_file = tmp_path / "config"
    config_file.write_text(
        "# keep this comment\nHEIC_FILE=/old.heic\nCACHE_DIR=/old-cache\n"
        "SCREEN_IDS=0,1\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache-home"))
    library.install_local_wallpaper(source, name="fuji", root=root)

    entry = library.activate_wallpaper(
        "fuji", root=root, config_file=config_file
    )

    text = config_file.read_text(encoding="utf-8")
    assert f"HEIC_FILE={entry.heic_file}" in text
    assert f"CACHE_DIR={entry.cache_dir}" in text
    assert "SCREEN_IDS=0,1" in text
    assert "# keep this comment" in text


def test_active_installed_id_matches_configured_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "fuji.heic"
    source.write_bytes(b"heic")
    root = tmp_path / "library"
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache-home"))
    entry = library.install_local_wallpaper(source, name="fuji", root=root)

    assert library.active_installed_id(entry.heic_file, root) == "fuji"
    assert library.active_installed_id(tmp_path / "other.heic", root) is None
