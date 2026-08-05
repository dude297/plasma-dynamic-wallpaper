# Distribution packaging

PyPI and `pipx` remain the recommended cross-distribution installation path.
The repository also provides reproducible Debian and Arch package inputs.

## Clean release build

The release helper removes stale `dist/`, `build/`, and root `*.egg-info`
artifacts before building. This prevents old package versions from being picked
up by shell globs or pip's dependency resolver.

```bash
python scripts/release.py all --native
```

Add `--require-clean` to require a committed working tree:

```bash
python scripts/release.py all --native --require-clean
```

The helper runs Ruff, tests, compilation, whitespace checks, Python builds,
Twine validation, the Debian builder, and the Arch PKGBUILD renderer.

## Debian package

Build from scratch:

```bash
packaging/debian/build-deb.sh
```

Reuse an already built exact-version wheel:

```bash
packaging/debian/build-deb.sh --no-python-build
```

The script selects the wheel matching the version in `pyproject.toml`; it never
passes every wheel in `dist/` to pip. The resulting package is written to:

```text
dist/plasma-dynamic-wallpaper_VERSION_all.deb
```

It installs the Python command globally. Each desktop user still runs
`dynamic-wallpaper --setup` to install user-level configuration and systemd
units.

## Arch Linux PKGBUILD

Build the source archive and pass its exact path:

```bash
python -m build --sdist
version="$(python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')"
python scripts/render-pkgbuild.py \
  "dist/plasma_dynamic_wallpaper-${version}.tar.gz"
```

For an official tag, the rendered PKGBUILD points to the corresponding GitHub
source. Review distribution dependency names before publishing to the AUR.
