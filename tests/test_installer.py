"""Tests for wheel and pipx user setup."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from dynamic_wallpaper import installer


def test_install_user_writes_templates_without_enabling(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config_home = tmp_path / "config"
    data_home = tmp_path / "data"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
    monkeypatch.setattr(
        installer, "_command_path", Mock(return_value="/bin/pdw")
    )

    lines = installer.install_user(enable_timer=False)

    config = config_home / "dynamic-wallpaper" / "config"
    service = config_home / "systemd" / "user" / "dynamic-wallpaper.service"
    timer = config_home / "systemd" / "user" / "dynamic-wallpaper.timer"
    watch = (
        config_home / "systemd" / "user" / "dynamic-wallpaper-watch.service"
    )
    assert config.is_file()
    service_text = service.read_text(encoding="utf-8")
    assert "ExecStart=/bin/pdw --startup" in service_text
    assert "TimeoutStartSec=75s" in service_text
    assert "Restart=on-failure" in service_text
    assert "RestartSec=5s" in service_text
    timer_text = timer.read_text(encoding="utf-8")
    assert "OnStartupSec=15s" in timer_text
    assert "OnUnitInactiveSec=1min" in timer_text
    watch_text = watch.read_text(encoding="utf-8")
    assert "ExecStart=/bin/pdw --watch" in watch_text
    assert "Restart=always" in watch_text
    assert "Timer enabled: no" in lines
    assert "Watchdog enabled: no" in lines


def test_install_user_preserves_existing_config(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config_home = tmp_path / "config"
    config = config_home / "dynamic-wallpaper" / "config"
    config.parent.mkdir(parents=True)
    config.write_text("HEIC_FILE=/keep.heic\n", encoding="utf-8")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setattr(
        installer, "_command_path", Mock(return_value="/bin/pdw")
    )

    installer.install_user(enable_timer=False)

    assert config.read_text(encoding="utf-8") == "HEIC_FILE=/keep.heic\n"
