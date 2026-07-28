# Architecture

## Runtime flow

```text
configuration
     |
     v
WallpaperEngine
     |
     +--> metadata fingerprint/cache --> Apple h24 schedule
     |
     +--> HEIC frame cache -----------> frame-N.png
     |
     +--> scheduler ------------------> selected frame
     |
     +--> Plasma adapter -------------> unique render alias + D-Bus write
     |
     `--> state store ----------------> last successful application
```

## Components

### `config.py`

Loads the user configuration and validates the HEIC source and cache paths.

### `metadata.py`

Uses `exiftool` to decode Apple's embedded `apple_desktop:h24` metadata. The
decoded plist is cached with a source fingerprint so normal timer runs avoid a
new subprocess call.

### `cache.py`

Uses `heif-convert` to extract the source images. Cache replacement is designed
to avoid leaving a partially rebuilt frame set after interruption or failure.

### `scheduler.py`

Maps the requested local time to the embedded Apple schedule and returns the
corresponding extracted frame.

### `plasma.py`

Creates a unique hard-link or copied alias under `.plasma-render`, writes its
URI through `org.kde.PlasmaShell.evaluateScript`, calls `reloadConfig()`, and
verifies every desktop's read-back response. Old aliases are pruned.

### `state.py`

Stores the last successful frame and application timestamp. The engine uses it
to skip redundant updates unless `--force` is supplied.

### `diagnostics.py`

Implements `--doctor`, checking Python, required executables, configuration,
source readability, and cache writability.

## Cache layout

```text
~/.cache/dynamic-wallpaper/
├── state.json
└── Fuji/
    ├── frame-1.png
    ├── frame-2.png
    ├── ...
    ├── metadata cache files
    └── .plasma-render/
        ├── frame-2-<unique-id>.png
        └── ... newest aliases only
```

## Failure boundaries

Frame extraction and metadata decoding happen before the Plasma write. State is
saved only after Plasma confirms the requested URI. This keeps a failed desktop
update from being recorded as successful.
