# Release checklist

1. Update `pyproject.toml` and add a non-empty matching `CHANGELOG.md` section.
2. Run the complete clean validation:

   ```bash
   python scripts/release.py all --native --require-clean
   ```

3. Inspect the wheel, source archive, Debian package, and `dist/PKGBUILD`.
4. Install the wheel into a clean virtual environment and smoke-test
   `--version`, `--doctor`, `--current`, and `--schedule`.
5. Test login, Plasma restart, suspend/resume, and monitor disconnect/reconnect.
6. Tag `vX.Y.Z-rcN` for a GitHub prerelease and complete a soak test.
7. Tag `vX.Y.Z` for the stable GitHub and PyPI release.

The release helper deliberately does not create or push Git tags. Tagging stays
an explicit maintainer action after artifacts have been inspected.
