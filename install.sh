#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

INSTALL_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/dynamic-wallpaper"
BIN_DIR="$HOME/.local/bin"
SYSTEMD_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/dynamic-wallpaper"

echo "Installing dynamic-wallpaper..."

for command in python3 exiftool heif-convert qdbus6; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "Missing dependency: $command" >&2
        exit 1
    fi
done

mkdir -p \
    "$INSTALL_ROOT" \
    "$BIN_DIR" \
    "$SYSTEMD_DIR" \
    "$CONFIG_DIR"

rm -rf "$INSTALL_ROOT/dynamic_wallpaper"

cp -r \
    "$PROJECT_ROOT/dynamic_wallpaper" \
    "$INSTALL_ROOT/dynamic_wallpaper"

cat > "$BIN_DIR/dynamic-wallpaper" <<LAUNCHER
#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

INSTALL_ROOT = Path("$INSTALL_ROOT")

if str(INSTALL_ROOT) not in sys.path:
    sys.path.insert(0, str(INSTALL_ROOT))

from dynamic_wallpaper.cli import main

raise SystemExit(main())
LAUNCHER

chmod +x "$BIN_DIR/dynamic-wallpaper"

install -m 0644 \
    "$PROJECT_ROOT/systemd/dynamic-wallpaper.service" \
    "$SYSTEMD_DIR/dynamic-wallpaper.service"

install -m 0644 \
    "$PROJECT_ROOT/systemd/dynamic-wallpaper.timer" \
    "$SYSTEMD_DIR/dynamic-wallpaper.timer"

if [[ ! -f "$CONFIG_DIR/config" ]]; then
    install -m 0644 \
        "$PROJECT_ROOT/config/config.example" \
        "$CONFIG_DIR/config"

    echo
    echo "Created configuration:"
    echo "  $CONFIG_DIR/config"
    echo
    echo "Edit HEIC_FILE before starting the timer."
fi

systemctl --user daemon-reload
systemctl --user enable --now dynamic-wallpaper.timer

echo
echo "Installation complete."
echo "Command: $BIN_DIR/dynamic-wallpaper"
echo "Timer:   dynamic-wallpaper.timer"
