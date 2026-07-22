# Dynamic Wallpaper for KDE Plasma

A lightweight Linux utility that uses the embedded schedule in Apple Dynamic Desktop HEIC wallpapers to update KDE Plasma automatically throughout the day.

The application extracts the HEIC frames, decodes Apple's `apple_desktop:h24` metadata, selects the correct frame for the current time, and applies it to KDE Plasma.

## Features

- Reads Apple Dynamic Desktop HEIC files
- Decodes embedded Apple `h24` schedule metadata
- Extracts and caches HEIC frames automatically
- Applies the correct wallpaper based on local time
- Supports KDE Plasma
- Runs automatically with a user-level systemd timer
- Avoids reapplying an unchanged frame
- Includes schedule inspection, dry-run, and forced-update commands
- Does not require root privileges

## Requirements

The following commands must be installed:

- `python3`
- `exiftool`
- `heif-convert`
- `qdbus6`
- `systemctl`

On Ubuntu or Kubuntu, the main dependencies can typically be installed with:

```bash
sudo apt install python3 libimage-exiftool-perl libheif-examples qdbus-qt6

