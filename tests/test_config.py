"""Tests for dynamic wallpaper configuration loading."""

from pathlib import Path

import pytest

from dynamic_wallpaper.config import Config, _parse_assignment, load_config


def test_parse_assignment_ignores_blank_comments_and_invalid_lines() -> None:
    assert _parse_assignment("") is None
    assert _parse_assignment("   # comment") is None
    assert _parse_assignment("NOT_AN_ASSIGNMENT") is None


def test_parse_assignment_trims_and_unquotes_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WALLPAPER_ROOT", "/wallpapers")

    assert _parse_assignment(' HEIC_FILE = "$WALLPAPER_ROOT/Fuji.heic" ') == (
        "HEIC_FILE",
        "/wallpapers/Fuji.heic",
    )


def test_parse_assignment_preserves_additional_equals() -> None:
    assert _parse_assignment("TOKEN=left=right") == (
        "TOKEN",
        "left=right",
    )


def test_parse_assignment_expands_home(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    assert _parse_assignment("CACHE_DIR=~/frames") == (
        "CACHE_DIR",
        str(tmp_path / "frames"),
    )


def test_load_config_reads_required_values(tmp_path: Path) -> None:
    config_file = tmp_path / "config"
    config_file.write_text(
        "HEIC_FILE=/wallpapers/Fuji.heic\n"
        "CACHE_DIR=/tmp/dynamic-wallpaper\n",
        encoding="utf-8",
    )

    assert load_config(config_file) == Config(
        heic_file=Path("/wallpapers/Fuji.heic"),
        cache_dir=Path("/tmp/dynamic-wallpaper"),
    )


def test_load_config_uses_last_duplicate_setting(tmp_path: Path) -> None:
    config_file = tmp_path / "config"
    config_file.write_text(
        "HEIC_FILE=/old.heic\n"
        "HEIC_FILE=/new.heic\n"
        "CACHE_DIR=/cache\n",
        encoding="utf-8",
    )

    assert load_config(config_file).heic_file == Path("/new.heic")


def test_load_config_uses_xdg_default_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config_file = tmp_path / "dynamic-wallpaper" / "config"
    config_file.parent.mkdir()
    config_file.write_text(
        "HEIC_FILE=/wallpaper.heic\nCACHE_DIR=/cache\n",
        encoding="utf-8",
    )

    config = load_config()

    assert config.heic_file == Path("/wallpaper.heic")
    assert config.cache_dir == Path("/cache")


def test_load_config_rejects_missing_file(tmp_path: Path) -> None:
    config_file = tmp_path / "missing"

    with pytest.raises(
        FileNotFoundError,
        match="Configuration file not found",
    ):
        load_config(config_file)


@pytest.mark.parametrize("missing_key", ["HEIC_FILE", "CACHE_DIR"])
def test_load_config_rejects_missing_required_setting(
    tmp_path: Path,
    missing_key: str,
) -> None:
    values = {
        "HEIC_FILE": "/wallpaper.heic",
        "CACHE_DIR": "/cache",
    }
    values.pop(missing_key)
    config_file = tmp_path / "config"
    config_file.write_text(
        "".join(f"{key}={value}\n" for key, value in values.items()),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=missing_key):
        load_config(config_file)
