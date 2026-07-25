"""Operational readiness checks for dynamic-wallpaper."""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from .config import Config, load_config, validate_config


@dataclass(frozen=True)
class DiagnosticResult:
    """Represent one readiness check and its user-facing detail."""

    name: str
    ok: bool
    detail: str

    def format(self) -> str:
        """Return a stable, terminal-friendly diagnostic line."""
        status = "OK" if self.ok else "FAIL"
        return f"[{status}] {self.name}: {self.detail}"


def _command_check(command: str) -> DiagnosticResult:
    path = shutil.which(command)
    if path is None:
        return DiagnosticResult(
            name=command,
            ok=False,
            detail="not found in PATH",
        )

    return DiagnosticResult(name=command, ok=True, detail=path)


def _config_checks() -> list[DiagnosticResult]:
    try:
        config = load_config()
        validate_config(config)
    except (FileNotFoundError, OSError, ValueError) as exc:
        return [
            DiagnosticResult(
                name="configuration",
                ok=False,
                detail=str(exc),
            )
        ]

    return [
        DiagnosticResult(
            name="configuration",
            ok=True,
            detail="loaded and valid",
        ),
        _heic_check(config),
        _cache_check(config),
    ]


def _heic_check(config: Config) -> DiagnosticResult:
    if config.heic_file.is_file():
        return DiagnosticResult(
            name="HEIC wallpaper",
            ok=True,
            detail=str(config.heic_file),
        )

    return DiagnosticResult(
        name="HEIC wallpaper",
        ok=False,
        detail=f"file not found: {config.heic_file}",
    )


def _cache_check(config: Config) -> DiagnosticResult:
    cache_dir = config.cache_dir

    if cache_dir.exists():
        if cache_dir.is_dir() and os.access(cache_dir, os.W_OK):
            return DiagnosticResult(
                name="cache directory",
                ok=True,
                detail=f"writable: {cache_dir}",
            )

        return DiagnosticResult(
            name="cache directory",
            ok=False,
            detail=f"not a writable directory: {cache_dir}",
        )

    parent = _nearest_existing_parent(cache_dir)
    if parent.is_dir() and os.access(parent, os.W_OK):
        return DiagnosticResult(
            name="cache directory",
            ok=True,
            detail=f"can be created: {cache_dir}",
        )

    return DiagnosticResult(
        name="cache directory",
        ok=False,
        detail=f"cannot be created under: {parent}",
    )


def _nearest_existing_parent(path: Path) -> Path:
    candidate = path
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate


def run_diagnostics() -> tuple[list[str], bool]:
    """Run readiness checks and return formatted output and overall status."""
    results = [
        DiagnosticResult(
            name="Python",
            ok=sys.version_info >= (3, 12),
            detail=sys.version.split()[0],
        ),
        _command_check("exiftool"),
        _command_check("heif-convert"),
        _command_check("qdbus6"),
        *_config_checks(),
    ]

    return [result.format() for result in results], all(
        result.ok for result in results
    )
