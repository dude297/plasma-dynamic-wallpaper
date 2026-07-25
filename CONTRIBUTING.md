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

## Preparing a release

Releases use the version in `pyproject.toml` as the single source of truth.
Before tagging a release:

1. Update `version` in `pyproject.toml`.
2. Move the completed entries from `[Unreleased]` into a matching, dated
   `CHANGELOG.md` section.
3. Run every command under **Quality checks**.
4. Commit and push the release preparation changes.
5. Create and push the exact matching tag, such as `v0.1.0`.

```bash
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0
```

The release workflow verifies the tag, package version, changelog, lint, tests,
coverage, package metadata, and installed command before creating the GitHub
Release. PyPI publishing is intentionally not enabled.
