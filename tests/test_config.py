"""Tests for dynamic wallpaper configuration loading."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from dynamic_wallpaper.config import (
    Config,
    _parse_assignment,
    config_path,
    load_config,
    validate_config,
)


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
        "HEIC_FILE=/wallpapers/Fuji.heic\nCACHE_DIR=/tmp/dynamic-wallpaper\n",
        encoding="utf-8",
    )

    assert load_config(config_file) == Config(
        heic_file=Path("/wallpapers/Fuji.heic"),
        cache_dir=Path("/tmp/dynamic-wallpaper"),
    )


def test_load_config_uses_last_duplicate_setting(tmp_path: Path) -> None:
    config_file = tmp_path / "config"
    config_file.write_text(
        "HEIC_FILE=/old.heic\nHEIC_FILE=/new.heic\nCACHE_DIR=/cache\n",
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


def test_validate_config_accepts_heic_and_directory(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    validate_config(Config(tmp_path / "wallpaper.HEIC", cache_dir))


def test_validate_config_rejects_non_heic_file(tmp_path: Path) -> None:
    config = Config(tmp_path / "wallpaper.jpg", tmp_path / "cache")

    with pytest.raises(ValueError, match="HEIC_FILE must point"):
        validate_config(config)


def test_validate_config_rejects_cache_file(tmp_path: Path) -> None:
    cache_file = tmp_path / "cache"
    cache_file.write_text("not a directory", encoding="utf-8")
    config = Config(tmp_path / "wallpaper.heic", cache_file)

    with pytest.raises(ValueError, match="CACHE_DIR must point"):
        validate_config(config)


def test_config_path_uses_xdg_config_home(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    assert config_path() == tmp_path / "dynamic-wallpaper" / "config"


def test_config_path_defaults_to_user_config_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setattr(Path, "home", Mock(return_value=tmp_path))

    assert config_path() == tmp_path / ".config/dynamic-wallpaper/config"


def test_load_config_reads_optional_screen_ids(tmp_path: Path) -> None:
    config_file = tmp_path / "config"
    config_file.write_text(
        "HEIC_FILE=/wallpaper.heic\nCACHE_DIR=/cache\nSCREEN_IDS=0, 2\n",
        encoding="utf-8",
    )

    assert load_config(config_file).screen_ids == (0, 2)


@pytest.mark.parametrize("value", ["left", "0,left"])
def test_load_config_rejects_invalid_screen_ids(
    tmp_path: Path, value: str
) -> None:
    config_file = tmp_path / "config"
    config_file.write_text(
        f"HEIC_FILE=/wallpaper.heic\nCACHE_DIR=/cache\nSCREEN_IDS={value}\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="SCREEN_IDS must be"):
        load_config(config_file)


@pytest.mark.parametrize("screen_ids", [(-1,), (0, 0)])
def test_validate_config_rejects_invalid_screen_selection(
    tmp_path: Path, screen_ids: tuple[int, ...]
) -> None:
    config = Config(
        tmp_path / "wallpaper.heic", tmp_path / "cache", screen_ids
    )

    with pytest.raises(ValueError, match="SCREEN_IDS"):
        validate_config(config)
