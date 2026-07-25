# Contributing

Thank you for helping improve Plasma Dynamic Wallpaper.

## Development setup

```bash
git clone https://github.com/dude297/plasma-dynamic-wallpaper.git
cd plasma-dynamic-wallpaper
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Quality checks

Run the same checks used by CI before opening a pull request:

```bash
python -m ruff check .
python -m ruff format --check .
python -m pytest
python -m pytest --cov=dynamic_wallpaper --cov-report=term-missing
python -m build
python -m twine check dist/*
git diff --check
```

Use `python -m ruff format .` to apply formatting and
`python -m ruff check . --fix` for safe automatic lint fixes.

## Pull requests

Keep changes focused, add or update tests for behavior changes, and update the
README or changelog when user-visible behavior changes. Avoid committing build
artifacts, extracted wallpaper frames, or local configuration.
