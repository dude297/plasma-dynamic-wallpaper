# Installation

## Supported environment

Plasma Dynamic Wallpaper is designed for a user session running KDE Plasma 6
on Linux with user-level systemd available. Python 3.12 or newer is required.

On Ubuntu or Kubuntu, install the external tools first:

```bash
sudo apt install python3 libimage-exiftool-perl libheif-examples qdbus-qt6
```

The runtime commands are:

- `exiftool` for Apple Dynamic Desktop metadata
- `heif-convert` for HEIC frame extraction
- `qdbus6` for Plasma wallpaper configuration
- `systemctl --user` for scheduled updates

## Repository installer

```bash
git clone https://github.com/dude297/plasma-dynamic-wallpaper.git
cd plasma-dynamic-wallpaper
./install.sh
```

For unattended installation:

```bash
./install.sh --yes
```

To install files without enabling the timer:

```bash
./install.sh --no-enable
```

The installer preserves an existing configuration by creating a timestamped
backup before replacing managed files.

## Configuration

Create or edit:

```text
~/.config/dynamic-wallpaper/config
```

Example:

```bash
HEIC_FILE="$HOME/Pictures/DynamicWallpapers/Fuji/Fuji.heic"
CACHE_DIR="$HOME/.cache/dynamic-wallpaper/Fuji"
```

Paths may contain spaces when quoted. The cache directory should be writable by
the current desktop user.

## Verify the installation

```bash
dynamic-wallpaper --doctor
dynamic-wallpaper --config
dynamic-wallpaper --schedule
dynamic-wallpaper --force --verbose
systemctl --user status dynamic-wallpaper.timer
```

A healthy forced run should report the selected frame, create a unique
`.plasma-render` alias, and confirm that Plasma retained the requested URI.

## Updating

```bash
git pull
./install.sh
```

## Uninstalling

```bash
./uninstall.sh
```

Configuration and cache data are retained by default. Remove them too with:

```bash
./uninstall.sh --purge
```
