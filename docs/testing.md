# Testing

## Standard test suite

```bash
python -m ruff check .
python -m ruff format --check .
python -m pytest
python -m pytest --cov=dynamic_wallpaper --cov-report=term-missing
```

The normal suite mocks external commands and is safe to run on any supported
Python environment. Live desktop tests are skipped by default.

## Live Plasma integration test

The integration test changes the current wallpaper briefly and restores the
previous URI after verification. Run it only from an active KDE Plasma user
session:

```bash
PDW_RUN_LIVE_PLASMA_TESTS=1 \
python -m pytest tests/integration/test_live_plasma.py -m integration -vv
```

Requirements:

- an active `plasmashell`
- a working session D-Bus address
- `qdbus6` available on `PATH`
- permission to modify the current user's wallpaper

The test creates a temporary one-pixel PNG, applies it through the production
`set_wallpaper()` function, verifies that every desktop reports a unique
`.plasma-render` URI, and restores the original wallpaper configuration.

## GitHub Actions runner

`.github/workflows/live-plasma.yml` is manual because GitHub-hosted Linux
runners do not provide a persistent interactive Plasma session. It targets a
self-hosted runner with these labels:

```text
self-hosted
linux
kde-plasma
```

Install the runner under the same user that owns the Plasma session and ensure
its service environment can access `DBUS_SESSION_BUS_ADDRESS`. Trigger **Live
Plasma Integration** manually from the Actions tab after the session is ready.
