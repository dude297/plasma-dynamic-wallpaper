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
make check
python -m pytest --cov=dynamic_wallpaper --cov-report=term-missing
python -m build
python -m twine check dist/*
git diff --check
```

The opt-in live Plasma test and self-hosted runner requirements are documented
in [docs/testing.md](docs/testing.md).

Use `make fix` to apply Ruff fixes (including explicitly opted-in
unsafe fixes) and formatting. Review the resulting diff, then run
`make check`; CI invokes the same shared quality gate.

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
3. Run `python scripts/release.py all --native --require-clean`.
4. Commit and push the release preparation changes.
5. Create and push the exact matching tag, such as `v0.1.0`, or a release-candidate tag such as `v0.1.0-rc6`.

```bash
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0
```

The release workflow verifies the tag, package version, changelog, lint, tests,
coverage, package metadata, and installed command before creating the GitHub
Release. Stable tags publish to PyPI through trusted publishing; RC tags remain
GitHub prereleases.

## Community and security

Participation is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Report
security-sensitive problems privately according to [SECURITY.md](SECURITY.md).
Use the issue templates for public bugs and feature requests, and avoid sharing
private HEIC files or unredacted user-session data.
