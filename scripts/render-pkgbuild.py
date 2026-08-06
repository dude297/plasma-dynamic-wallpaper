"""Render an Arch PKGBUILD from a tagged source archive."""

from __future__ import annotations

import argparse
import hashlib
import tomllib
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path, default=Path("dist/PKGBUILD"))
    args = parser.parse_args()

    version = tomllib.loads(
        Path("pyproject.toml").read_text(encoding="utf-8")
    )["project"]["version"]
    digest = hashlib.sha256(args.archive.read_bytes()).hexdigest()
    template = Path("packaging/arch/PKGBUILD.in").read_text(encoding="utf-8")
    rendered = template.replace("@VERSION@", version).replace(
        "@SHA256@", digest
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
