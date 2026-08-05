# Distribution packaging

PyPI and `pipx` remain the recommended cross-distribution installation path.
The repository also contains reproducible starting points for native packages.

## Debian package

Install build tooling, then run:

```bash
python -m pip install -e ".[dev]"
packaging/debian/build-deb.sh
```

The package is written to `dist/`. It installs the Python command globally;
each desktop user still runs `dynamic-wallpaper --setup` to create and enable
user-level systemd units.

## Arch Linux PKGBUILD

Build the source distribution, then render a checksummed PKGBUILD:

```bash
python -m build --sdist
python scripts/render-pkgbuild.py dist/*.tar.gz
```

For an official tag, the PKGBUILD source URL points to the matching GitHub tag.
Review distribution dependency names before publishing to the AUR.
