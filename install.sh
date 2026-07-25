#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

INSTALL_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/dynamic-wallpaper"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
SYSTEMD_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/dynamic-wallpaper"
CONFIG_PATH="$CONFIG_DIR/config"

ASSUME_YES=false
ENABLE_TIMER=true

usage() {
    cat <<'USAGE'
Usage: ./install.sh [OPTIONS]

Install plasma-dynamic-wallpaper for the current user.

Options:
  -y, --yes       Skip the confirmation prompt.
      --no-enable Install files without enabling or starting the timer.
  -h, --help      Show this help message.
USAGE
}

while (($# > 0)); do
    case "$1" in
        -y | --yes)
            ASSUME_YES=true
            ;;
        --no-enable)
            ENABLE_TIMER=false
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

missing=()
for command in python3 exiftool heif-convert qdbus6 systemctl; do
    if ! command -v "$command" >/dev/null 2>&1; then
        missing+=("$command")
    fi
done

if ((${#missing[@]} > 0)); then
    echo "Missing required dependencies:" >&2
    printf '  - %s\n' "${missing[@]}" >&2
    echo >&2
    echo "Install the missing commands, then run the installer again." >&2
    exit 1
fi

if [[ "$ENABLE_TIMER" == true ]] && ! systemctl --user show-environment >/dev/null 2>&1; then
    echo "Unable to contact the user systemd manager." >&2
    echo "Log in to a graphical Plasma session or use --no-enable." >&2
    exit 1
fi

if [[ "$ASSUME_YES" != true ]]; then
    cat <<EOF_CONFIRM
Install plasma-dynamic-wallpaper for the current user?

  Application: $INSTALL_ROOT
  Command:     $BIN_DIR/dynamic-wallpaper
  Config:      $CONFIG_PATH
  Timer:       $ENABLE_TIMER

EOF_CONFIRM
    read -r -p "Continue? [y/N] " reply
    case "$reply" in
        y | Y | yes | YES) ;;
        *)
            echo "Installation cancelled."
            exit 0
            ;;
    esac
fi

echo "Installing dynamic-wallpaper..."

mkdir -p \
    "$INSTALL_ROOT" \
    "$BIN_DIR" \
    "$SYSTEMD_DIR" \
    "$CONFIG_DIR"

if [[ -f "$CONFIG_PATH" ]]; then
    backup_path="$CONFIG_PATH.backup-$(date -u +%Y%m%dT%H%M%SZ)"
    cp -p "$CONFIG_PATH" "$backup_path"
    echo "Backed up existing configuration:"
    echo "  $backup_path"
fi

rm -rf "$INSTALL_ROOT/dynamic_wallpaper"
cp -r "$PROJECT_ROOT/dynamic_wallpaper" "$INSTALL_ROOT/dynamic_wallpaper"

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

if [[ ! -f "$CONFIG_PATH" ]]; then
    install -m 0644 "$PROJECT_ROOT/config/config.example" "$CONFIG_PATH"

    echo
    echo "Created configuration:"
    echo "  $CONFIG_PATH"
    echo
    echo "Edit HEIC_FILE before starting the timer."
fi

systemctl --user daemon-reload

if [[ "$ENABLE_TIMER" == true ]]; then
    systemctl --user enable --now dynamic-wallpaper.timer
else
    echo "Timer installation complete; enable it later with:"
    echo "  systemctl --user enable --now dynamic-wallpaper.timer"
fi

echo
echo "Installation complete."
echo "Command: $BIN_DIR/dynamic-wallpaper"
echo "Timer:   dynamic-wallpaper.timer"
