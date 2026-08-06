# Plasma Dynamic Wallpaper

[![CI](https://github.com/dude297/plasma-dynamic-wallpaper/actions/workflows/ci.yml/badge.svg)](https://github.com/dude297/plasma-dynamic-wallpaper/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/plasma-dynamic-wallpaper)](https://pypi.org/project/plasma-dynamic-wallpaper/)
[![Python](https://img.shields.io/pypi/pyversions/plasma-dynamic-wallpaper)](https://pypi.org/project/plasma-dynamic-wallpaper/)
[![License](https://img.shields.io/github/license/dude297/plasma-dynamic-wallpaper)](LICENSE)
[![KDE Plasma 6](https://img.shields.io/badge/KDE%20Plasma-6-1d99f3)](https://kde.org/plasma-desktop/)

Use Apple Dynamic Desktop HEIC wallpapers on KDE Plasma while preserving the
embedded `apple_desktop:h24` timeline—or align the same frames with local dawn,
solar noon, and dusk.

![Plasma Dynamic Wallpaper demo](docs/demo.gif)

## Highlights

- Decodes Apple Dynamic Desktop metadata directly.
- Supports embedded and solar-aware schedules.
- Extracts frames once and reuses source-aware caches.
- Reconciles the active wallpaper after login, resume, display changes, and
  Plasma Shell restarts.
- Handles active multi-monitor layouts and ignores detached containments.
- Includes a managed local wallpaper library.
- Provides user-level systemd timer and watchdog services.
- Offers diagnostics, status, cache maintenance, and dry-run commands.
- Uses atomic state and configuration writes.
- Requires no root access for normal operation.

## Quick start

### pipx (recommended)

Install the Python package in an isolated environment:

```bash
pipx install plasma-dynamic-wallpaper
dynamic-wallpaper --setup
```

Import and activate a wallpaper:

```bash
dynamic-wallpaper install ~/Pictures/Fuji.heic --name fuji
dynamic-wallpaper use fuji
dynamic-wallpaper --force
```

### From source

```bash
git clone https://github.com/dude297/plasma-dynamic-wallpaper.git
cd plasma-dynamic-wallpaper
./install.sh
```

Ubuntu and Kubuntu dependencies:

```bash
sudo apt install python3 libimage-exiftool-perl libheif-examples qdbus-qt6
```

See the [installation guide](docs/installation.md) for updating, uninstalling,
and native package notes.

## Common commands

| Command | Purpose |
| --- | --- |
| `dynamic-wallpaper --doctor` | Check dependencies, configuration, and cache access. |
| `dynamic-wallpaper --current` | Compare the scheduled frame with active Plasma desktops. |
| `dynamic-wallpaper --schedule` | Show today's resolved embedded or solar schedule. |
| `dynamic-wallpaper --status` | Show the last successful wallpaper application. |
| `dynamic-wallpaper --config` | Show resolved paths, screens, and schedule mode. |
| `dynamic-wallpaper --inspect` | Print decoded Apple metadata. |
| `dynamic-wallpaper --cache-status` | Check frame-cache freshness and integrity. |
| `dynamic-wallpaper --rebuild-cache` | Replace cached frames from the source HEIC. |
| `dynamic-wallpaper --at 18:00 --dry-run` | Preview selection for a specific time. |
| `dynamic-wallpaper --startup` | Wait for Plasma and reapply the current frame. |
| `dynamic-wallpaper --force --verbose` | Force an update with detailed diagnostics. |

### Managed wallpapers

```bash
dynamic-wallpaper install ~/Pictures/Fuji.heic --name fuji
dynamic-wallpaper install ~/Pictures/Sonoma.heic --name sonoma
dynamic-wallpaper list
dynamic-wallpaper use sonoma
dynamic-wallpaper remove fuji
```

Each managed wallpaper receives an isolated source directory and cache. The
active entry is marked with `*` in `dynamic-wallpaper list`.

## Scheduling

### Embedded schedule

The default mode follows the transition times stored in Apple's HEIC metadata:

```ini
SCHEDULE_MODE=embedded
```

### Solar-aware schedule

Solar mode preserves the original frame order but maps its day anchors to local
civil dawn, solar noon, and civil dusk:

```ini
SCHEDULE_MODE=solar
LATITUDE=37.3382
LONGITUDE=-121.8863
```

Coordinates are decimal degrees; west longitudes are negative. The calculation
is local and does not require network access. At polar dates without civil dawn
or dusk, the command reports an actionable error rather than silently choosing
an incorrect frame.

Inspect the resolved timeline with:

```bash
dynamic-wallpaper --schedule
dynamic-wallpaper --current
```

## Multi-monitor behavior

By default, all currently active Plasma screens are detected automatically.
Detached containments reported as `screen=-1` are ignored and retried when they
become active again. To restrict updates, set explicit screen IDs:

```ini
SCREEN_IDS=0,1
```

## Reliability services

`dynamic-wallpaper --setup` installs two user services:

- `dynamic-wallpaper.timer` reconciles the schedule every minute.
- `dynamic-wallpaper-watch.service` requests immediate recovery after Plasma
  returns on D-Bus or the machine resumes from sleep.

Useful checks:

```bash
systemctl --user status dynamic-wallpaper.timer --no-pager
systemctl --user status dynamic-wallpaper-watch.service --no-pager
journalctl --user -u dynamic-wallpaper.service -n 50 --no-pager
journalctl --user -u dynamic-wallpaper-watch.service -n 50 --no-pager
```

## How it works

```text
Apple HEIC
    │
    ▼
metadata decoder ──► embedded or solar scheduler
    │                         │
    ▼                         ▼
source-aware frame cache ─► selected PNG
                              │
                              ▼
                    Plasma D-Bus adapter
                              │
                              ▼
                 active desktop containments
```

The engine verifies Plasma's read-back response before saving state. Unique
render aliases avoid stale image-provider caches, while active aliases are
protected from cleanup.

More detail: [Architecture](docs/architecture.md).

## Troubleshooting

Start with:

```bash
dynamic-wallpaper --doctor
dynamic-wallpaper --current
```

| Symptom | First check |
| --- | --- |
| Wallpaper did not change | `dynamic-wallpaper --force --verbose` |
| Default wallpaper after login | `journalctl --user -u dynamic-wallpaper.service -b` |
| Recovery after sleep failed | Check `dynamic-wallpaper-watch.service`. |
| A monitor is skipped | Check Plasma screen IDs with `--current`; detached screens are expected to be inactive. |
| Cache looks damaged | Run `dynamic-wallpaper --cache-status`, then `--rebuild-cache`. |
| Solar schedule looks wrong | Verify latitude, longitude, local time zone, and `--schedule`. |

See [Troubleshooting](docs/troubleshooting.md) and [FAQ](docs/faq.md).

## Development

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

make check
python -m build
python -m twine check dist/*
```

Contribution and live-Plasma testing guidance:

- [Contributing](CONTRIBUTING.md)
- [Testing](docs/testing.md)
- [Release process](docs/release-process.md)
- [Packaging](docs/packaging.md)

## Roadmap

- **v0.3:** release polish, native packaging, richer diagnostics.
- **v0.4:** native KDE configuration UI and previews.
- **v0.5:** optional GeoClue-based location discovery and additional desktop
  backends.

Automatic location discovery is intentionally deferred: solar mode currently
uses explicit coordinates, stays offline, and avoids unexpected location access.

## License

Released under the [MIT License](LICENSE).
