# Plasma Dynamic Wallpaper

Bring Apple's Dynamic Desktop HEIC wallpapers to KDE Plasma.
Plasma Dynamic Wallpaper is one of the few Linux implementations that uses Apple's embedded apple_desktop:h24 metadata directly, preserving the original Dynamic Desktop schedule instead of approximating it.

## Features

- Apple Dynamic Desktop HEIC support
- Native `apple_desktop:h24` schedule decoding
- Automatic frame extraction and caching
- KDE Plasma integration
- User-level systemd timer
- Skips redundant wallpaper updates
- CLI for inspection and testing
- No root required

## Requirements

Ubuntu/Kubuntu:

```bash
sudo apt install python3 libimage-exiftool-perl libheif-examples qdbus-qt6
```

Requires:

- Python 3
- exiftool
- heif-convert
- qdbus6
- systemd

## Installation

```bash
git clone https://github.com/dude297/plasma-dynamic-wallpaper.git
cd plasma-dynamic-wallpaper

chmod +x install.sh
./install.sh
```

Configure:

```bash
~/.config/dynamic-wallpaper/config
```

Example:

```bash
HEIC_FILE="$HOME/Pictures/DynamicWallpapers/Fuji/Fuji.heic"
CACHE_DIR="$HOME/.cache/dynamic-wallpaper/Fuji"
```

## Usage

```bash
dynamic-wallpaper                 # Apply wallpaper
dynamic-wallpaper --schedule      # Show Apple schedule
dynamic-wallpaper --inspect       # View decoded metadata
dynamic-wallpaper --extract       # Extract frames only
dynamic-wallpaper --dry-run       # Preview selected frame
dynamic-wallpaper --at 18:00 --dry-run
dynamic-wallpaper --force
```

## Systemd

The installer enables a user timer that updates the wallpaper every five minutes.

```bash
systemctl --user status dynamic-wallpaper.timer
systemctl --user start dynamic-wallpaper.service
journalctl --user -u dynamic-wallpaper.service -n 20
```

## Project Layout

```text
plasma-dynamic-wallpaper/
├── bin/
├── config/
├── dynamic_wallpaper/
├── systemd/
├── install.sh
├── uninstall.sh
└── README.md
```

## Cache

```
~/.cache/dynamic-wallpaper/
```

The current wallpaper state is stored in:

```
~/.cache/dynamic-wallpaper/state.json
```

to avoid reapplying the same frame.

## Updating

```bash
git pull
./install.sh
```

## Uninstall

```bash
./uninstall.sh
```

User configuration and cache are preserved.

## Roadmap

- Multiple wallpaper collections
- Additional desktop environments
- Automated tests
- GitHub Actions
- Package distribution

## License

Released under the MIT License.
