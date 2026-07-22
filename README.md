# Plasma Dynamic Wallpaper

> Use Apple's Dynamic Desktop HEIC wallpapers on KDE Plasma.

Plasma Dynamic Wallpaper is a lightweight Python utility that brings Apple's Dynamic Desktop wallpapers to KDE Plasma.

Unlike most Linux implementations, it reads Apple's embedded `apple_desktop:h24` metadata directly instead of approximating sunrise/sunset times or using hardcoded schedules. The wallpaper changes automatically throughout the day according to the schedule embedded inside the HEIC file.

---

## Features

- ✅ Native support for Apple Dynamic Desktop HEIC wallpapers
- ✅ Reads embedded `apple_desktop:h24` metadata
- ✅ Uses Apple's actual frame schedule
- ✅ Automatic frame extraction and caching
- ✅ KDE Plasma integration
- ✅ User-level systemd timer
- ✅ Skips unnecessary wallpaper updates
- ✅ No root privileges required
- ✅ Command-line interface

---

## Demo

Morning:

```
07:30
↓
frame-1.png
```

Afternoon:

```
13:00
↓
frame-4.png
```

Night:

```
22:30
↓
frame-7.png
```

---

# Requirements

Required software:

- Python 3.10+
- exiftool
- libheif
- qdbus6
- systemd

Ubuntu / Kubuntu:

```bash
sudo apt install \
    python3 \
    libimage-exiftool-perl \
    libheif-examples \
    qdbus-qt6
```

---

# Installation

Clone the repository:

```bash
git clone https://github.com/dude297/plasma-dynamic-wallpaper.git

cd plasma-dynamic-wallpaper
```

Install:

```bash
chmod +x install.sh
./install.sh
```

The installer automatically:

- installs the Python package
- installs the command

```
~/.local/bin/dynamic-wallpaper
```

- installs the user service
- installs the systemd timer
- preserves existing configuration

---

# Configuration

Configuration file:

```
~/.config/dynamic-wallpaper/config
```

Example:

```bash
HEIC_FILE="$HOME/Pictures/DynamicWallpapers/Fuji/Fuji.heic"
CACHE_DIR="$HOME/.cache/dynamic-wallpaper/Fuji"
```

---

# Usage

Show schedule:

```bash
dynamic-wallpaper --schedule
```

Inspect embedded metadata:

```bash
dynamic-wallpaper --inspect
```

Extract frames:

```bash
dynamic-wallpaper --extract
```

Preview without changing wallpaper:

```bash
dynamic-wallpaper --dry-run
```

Preview a specific time:

```bash
dynamic-wallpaper --at 18:00 --dry-run
```

Force wallpaper update:

```bash
dynamic-wallpaper --force
```

Apply wallpaper immediately:

```bash
dynamic-wallpaper
```

---

# Automatic Updates

The installer enables a user timer:

```
dynamic-wallpaper.timer
```

Verify:

```bash
systemctl --user status dynamic-wallpaper.timer
```

Run once manually:

```bash
systemctl --user start dynamic-wallpaper.service
```

Recent logs:

```bash
journalctl --user \
    -u dynamic-wallpaper.service \
    -n 20
```

---

# Project Structure

```
plasma-dynamic-wallpaper
├── bin/
├── config/
├── dynamic_wallpaper/
├── systemd/
├── install.sh
├── uninstall.sh
└── README.md
```

---

# Cache

Extracted frames:

```
~/.cache/dynamic-wallpaper/
```

Current state:

```
~/.cache/dynamic-wallpaper/state.json
```

The state file prevents unnecessary wallpaper updates when the frame has not changed.

---

# Updating

After pulling new code:

```bash
git pull
./install.sh
```

Configuration and cache are preserved.

---

# Uninstall

```bash
./uninstall.sh
```

The uninstaller removes:

- installed command
- Python package
- systemd service
- timer

It intentionally leaves:

```
~/.config/dynamic-wallpaper/
~/.cache/dynamic-wallpaper/
```

---

# Roadmap

Planned features include:

- Multiple wallpaper collections
- Sunrise / sunset scheduling
- Additional desktop environment support
- Automated testing
- GitHub Actions CI
- Package distribution

---

# License

Released under the MIT License.
