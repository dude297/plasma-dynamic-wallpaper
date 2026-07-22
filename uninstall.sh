#!/usr/bin/env bash

set -euo pipefail

INSTALL_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/dynamic-wallpaper"
BIN_PATH="$HOME/.local/bin/dynamic-wallpaper"
SYSTEMD_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

echo "Uninstalling dynamic-wallpaper..."

systemctl --user disable --now dynamic-wallpaper.timer 2>/dev/null || true
systemctl --user stop dynamic-wallpaper.service 2>/dev/null || true

rm -f \
    "$SYSTEMD_DIR/dynamic-wallpaper.service" \
    "$SYSTEMD_DIR/dynamic-wallpaper.timer" \
    "$BIN_PATH"

rm -rf "$INSTALL_ROOT"

systemctl --user daemon-reload
systemctl --user reset-failed

echo
echo "dynamic-wallpaper has been uninstalled."
echo
echo "Preserved user data:"
echo "  ${XDG_CONFIG_HOME:-$HOME/.config}/dynamic-wallpaper"
echo "  ${XDG_CACHE_HOME:-$HOME/.cache}/dynamic-wallpaper"
echo
echo "Remove those directories manually if no longer needed."
