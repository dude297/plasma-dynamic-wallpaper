#!/usr/bin/env bash

set -euo pipefail

INSTALL_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/dynamic-wallpaper"
BIN_PATH="${XDG_BIN_HOME:-$HOME/.local/bin}/dynamic-wallpaper"
SYSTEMD_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/dynamic-wallpaper"
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/dynamic-wallpaper"

ASSUME_YES=false
PURGE=false

usage() {
    cat <<'USAGE'
Usage: ./uninstall.sh [OPTIONS]

Remove plasma-dynamic-wallpaper from the current user account.

Options:
  -y, --yes   Skip the confirmation prompt.
      --purge Also remove user configuration and cached frames.
  -h, --help  Show this help message.
USAGE
}

while (($# > 0)); do
    case "$1" in
        -y | --yes)
            ASSUME_YES=true
            ;;
        --purge)
            PURGE=true
            ;;
        -h | --help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
    shift
done

if [[ "$ASSUME_YES" != true ]]; then
    echo "Uninstall plasma-dynamic-wallpaper?"
    if [[ "$PURGE" == true ]]; then
        echo "Configuration and cached frames will also be removed."
    else
        echo "Configuration and cached frames will be preserved."
    fi
    echo
    read -r -p "Continue? [y/N] " reply
    case "$reply" in
        y | Y | yes | YES) ;;
        *)
            echo "Uninstall cancelled."
            exit 0
            ;;
    esac
fi

echo "Uninstalling dynamic-wallpaper..."

if command -v systemctl >/dev/null 2>&1; then
    systemctl --user disable --now dynamic-wallpaper.timer 2>/dev/null || true
    systemctl --user stop dynamic-wallpaper.service 2>/dev/null || true
fi

rm -f \
    "$SYSTEMD_DIR/dynamic-wallpaper.service" \
    "$SYSTEMD_DIR/dynamic-wallpaper.timer" \
    "$BIN_PATH"

rm -rf "$INSTALL_ROOT"

if [[ "$PURGE" == true ]]; then
    rm -rf "$CONFIG_DIR" "$CACHE_DIR"
fi

if command -v systemctl >/dev/null 2>&1; then
    systemctl --user daemon-reload 2>/dev/null || true
    systemctl --user reset-failed 2>/dev/null || true
fi

echo
echo "dynamic-wallpaper has been uninstalled."

if [[ "$PURGE" != true ]]; then
    echo
    echo "Preserved user data:"
    echo "  $CONFIG_DIR"
    echo "  $CACHE_DIR"
    echo
    echo "Run ./uninstall.sh --purge to remove those directories too."
fi
