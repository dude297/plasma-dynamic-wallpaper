# Plasma Dynamic Wallpaper

> Use Apple's Dynamic Desktop HEIC wallpapers on KDE Plasma.

![Demo](docs/demo.gif)
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

# Non-interactive install
./install.sh --yes

# Install files without enabling the timer
./install.sh --no-enable
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
dynamic-wallpaper --config        # Show active configuration paths
dynamic-wallpaper --status        # Show last applied wallpaper
dynamic-wallpaper --cache-status  # Show cache freshness and frame count
dynamic-wallpaper --rebuild-cache # Force frame re-extraction
dynamic-wallpaper --inspect       # View decoded metadata
dynamic-wallpaper --extract       # Extract frames only
dynamic-wallpaper --dry-run       # Preview selected frame
dynamic-wallpaper --at 18:00 --dry-run
dynamic-wallpaper --force
```

### Inspect active configuration

Show the configuration file and the resolved HEIC and cache paths:

```bash
dynamic-wallpaper --config
```

Primary information commands are mutually exclusive. For example,
`--status --schedule` is rejected instead of silently choosing one action.

### Manage the frame cache

Inspect cache freshness without modifying files:

```bash
dynamic-wallpaper --cache-status
```

Force a clean frame extraction when the HEIC was replaced without a detectable
timestamp change or cached output is suspected to be damaged:

```bash
dynamic-wallpaper --rebuild-cache
```

### Check installation health

Run the built-in readiness check before enabling the timer or when a scheduled
update fails:

```bash
dynamic-wallpaper --doctor
```

The command checks the Python version, required executables, configuration,
HEIC source file, and cache-directory readiness. It exits with status 1 when
any required check fails, so it can also be used in scripts.

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

User configuration and cache are preserved by default. To remove them too:

```bash
./uninstall.sh --purge
```

Both scripts prompt before making changes. Pass `--yes` for unattended use.
Existing configuration is backed up before every reinstall.

## Roadmap

- Multiple wallpaper collections
- Additional desktop environments
- PyPI publishing
- Signed release artifacts
- Additional desktop backends

## License

Released under the MIT License.

## Command version

```bash
dynamic-wallpaper --version
```

## Architecture

The CLI loads and validates configuration, then delegates orchestration to
`WallpaperEngine`. The engine coordinates four focused components:

1. `metadata.py` decodes Apple's embedded `apple_desktop:h24` data.
2. `cache.py` extracts HEIC frames and reuses a source-aware cache.
3. `scheduler.py` maps the current time to the correct frame.
4. `plasma.py` applies the selected image through Plasma's D-Bus interface.

`state.py` records the last applied frame and UTC application time so routine
timer runs can avoid redundant desktop updates and `--status` can report the
last successful change.

## Development

Create an isolated environment and install the project with development tools:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Run the standard checks:

```bash
python -m ruff check .
python -m ruff format --check .
python -m pytest
python -m pytest --cov=dynamic_wallpaper --cov-report=term-missing
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for package-build and pull-request
checks.

## Troubleshooting

### Configuration file not found

Create `~/.config/dynamic-wallpaper/config` from `config/config.example` and
confirm both required paths are set.

### `exiftool` or `heif-convert` not found

Install the Ubuntu/Kubuntu dependencies listed under Requirements, then verify:

```bash
exiftool -ver
heif-convert --help
```

### `qdbus6` not found or Plasma rejects the update

Confirm the command is installed and run the program from the active Plasma
user session. Inspect the service log with:

```bash
journalctl --user -u dynamic-wallpaper.service -n 50
```

### A wallpaper change is not detected

Run once with `--force`. If the source HEIC was replaced without its timestamp
changing, run `dynamic-wallpaper --rebuild-cache`.

## FAQ

### Does this modify the original HEIC file?

No. Frames and state are written only to the configured cache location.

### Does it require root access?

No. Installation, the systemd timer, cache, and Plasma update all run as the
current user.

### Why does the timer run every five minutes?

The embedded schedule selects discrete frames. Frequent lightweight checks keep
the desktop near the intended transition time, while state tracking prevents
unnecessary reapplication.

## Releases

Tagged releases are validated and published through GitHub Actions. Each
GitHub Release includes the installable wheel and source archive built from the
corresponding tag.

Release tags must exactly match the package version in `pyproject.toml`. For
example, package version `0.1.0` must use tag `v0.1.0`. The workflow also
requires a non-empty matching section in `CHANGELOG.md` and runs lint, tests,
coverage, build validation, and installed-command smoke tests before publishing.

PyPI publishing is not enabled yet. See [CONTRIBUTING.md](CONTRIBUTING.md) for
the maintainer release checklist.
