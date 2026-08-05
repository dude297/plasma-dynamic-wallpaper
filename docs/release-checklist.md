# Release checklist

1. Run `python -m ruff check .`, `python -m ruff format --check .`, and `python -m pytest`.
2. Build with `python -m build` and validate with `python -m twine check dist/*`.
3. Install the wheel into a clean virtual environment and smoke-test `--doctor`, `--current`, and `--version`.
4. Test login, Plasma restart, suspend/resume, and monitor disconnect/reconnect.
5. Verify `CHANGELOG.md` contains a non-empty section for the package version.
6. Tag `vX.Y.Z-rcN` for a GitHub prerelease, then `vX.Y.Z` for the stable PyPI release.
