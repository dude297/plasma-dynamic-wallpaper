#!/usr/bin/env python3
"""Run reproducible local release validation and artifact builds."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
BUILD = ROOT / "build"


def project_version() -> str:
    """Return the package version from pyproject.toml."""
    project = tomllib.loads(
        (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]
    return str(project["version"])


def run(*command: str) -> None:
    """Run a command from the repository root."""
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def clean() -> None:
    """Remove generated build and distribution artifacts."""
    for path in (DIST, BUILD):
        shutil.rmtree(path, ignore_errors=True)
    for path in ROOT.glob("*.egg-info"):
        shutil.rmtree(path, ignore_errors=True)


def quality_gate() -> None:
    """Run the checks required before building a release."""
    run(sys.executable, "-m", "ruff", "check", ".")
    run(sys.executable, "-m", "ruff", "format", "--check", ".")
    run(sys.executable, "-m", "pytest")
    run(sys.executable, "-m", "compileall", "-q", "dynamic_wallpaper", "tests")
    run("git", "diff", "--check")


def build_artifacts(*, native: bool) -> None:
    """Create and validate Python and optional native package artifacts."""
    clean()
    run(sys.executable, "-m", "build")
    run(sys.executable, "-m", "twine", "check", "dist/*")

    version = project_version()
    wheel = DIST / f"plasma_dynamic_wallpaper-{version}-py3-none-any.whl"
    source = DIST / f"plasma_dynamic_wallpaper-{version}.tar.gz"
    if not wheel.is_file() or not source.is_file():
        raise SystemExit(
            "Expected versioned wheel and source archive were not created."
        )

    if native:
        run("bash", "packaging/debian/build-deb.sh", "--no-python-build")
        run(
            sys.executable,
            "scripts/render-pkgbuild.py",
            str(source.relative_to(ROOT)),
        )


def validate_release_tree() -> None:
    """Require a clean Git tree before release tagging."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    if result.stdout.strip():
        raise SystemExit("Working tree is not clean; commit or stash changes.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate and build plasma-dynamic-wallpaper releases."
    )
    parser.add_argument(
        "command",
        choices=("check", "artifacts", "all"),
        help="checks only, artifacts only, or both",
    )
    parser.add_argument(
        "--native",
        action="store_true",
        help="also build Debian and Arch package metadata",
    )
    parser.add_argument(
        "--require-clean",
        action="store_true",
        help="fail unless the Git working tree is clean",
    )
    args = parser.parse_args()

    if args.require_clean:
        validate_release_tree()
    if args.command in {"check", "all"}:
        quality_gate()
    if args.command in {"artifacts", "all"}:
        build_artifacts(native=args.native)

    print(f"Release validation complete for {project_version()}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
