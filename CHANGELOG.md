# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- Keep watchdog lifecycle and recovery-reason logs visible in the user journal.

- The Plasma session watchdog now detects suspend/resume gaps using Linux boot time and immediately reapplies the current scheduled frame after wake.
- Resume recovery is coalesced with Plasma owner changes so one wake event triggers at most one service start.

### Packaging

- Prepare version 0.2.0 for `pipx` and PyPI installation.
- Publish stable tags to PyPI with GitHub trusted publishing while keeping RC tags GitHub-only.

### Added

- A lightweight Plasma D-Bus session watchdog requests immediate wallpaper recovery whenever Plasma Shell disappears and returns with a new owner.
- Managed multi-wallpaper commands: `list`, `install`, `use`, and `remove`.
- Isolated cache directories for each managed wallpaper.
- Atomic configuration switching that preserves screen-selection settings.

- `--current` reports the scheduled frame and verifies active Plasma desktop paths.

- Add active-screen autodetection and ignore inactive Plasma containments.
- Treat temporarily unavailable configured screens as retryable warnings.

### Added

- `pipx`-friendly `--setup` and `--setup-no-enable` commands that install
  packaged user configuration and systemd unit templates.
- Checksum-verified wallpaper library commands for catalog listing, search,
  installation, installed-file discovery, and removal.
- Configurable catalog source through `PDW_CATALOG_URL`, including local
  `file://` catalogs for development and mirrors.
- Wallpaper catalog schema and distribution guidance.

### Fixed

- Failed systemd one-shot runs retry after five seconds, and the user timer now reconciles Plasma state every minute for bounded crash and resume recovery.
- User systemd runs now wait for active Plasma desktop containments before
  selecting and force-applying the current frame, preventing login-time races
  and recalibrating after Plasma Shell restarts.
- Multi-monitor verification now returns one JSON document instead of
  concatenated per-screen objects.
- Screen targeting now updates only the requested Plasma containments.
- Render-alias cleanup preserves every file still referenced by a desktop.
- Timer runs reconcile persisted state with Plasma configuration, recovering
  automatically after logout, shell restart, or a missing render alias.
- External helper commands now have bounded timeouts instead of hanging a
  systemd oneshot indefinitely.

### Changed

- Package discovery now includes application data templates required by wheel
  and pipx installations.

## [0.1.0] - 2026-07-27

### Added

- Initial KDE Plasma dynamic HEIC wallpaper implementation.
- Apple `apple_desktop:h24` metadata decoding.
- Frame extraction, caching, scheduling, state tracking, and systemd integration.
- CLI `--version` option and actionable configuration validation.
- `dynamic-wallpaper --doctor` readiness checks for dependencies,
  configuration, wallpaper access, and cache-directory availability.
- `dynamic-wallpaper --status` reporting for the last successfully applied
  frame, timestamp, and cached wallpaper availability.
- `dynamic-wallpaper --config` output for the active configuration file, HEIC
  source, and cache directory.
- `dynamic-wallpaper --cache-status` reporting for cache freshness and
  extracted frame count.
- `dynamic-wallpaper --rebuild-cache` for forced frame re-extraction without
  manual cache deletion.
- `--verbose` diagnostics covering configuration, cache preparation, frame
  selection, Plasma DBus verification, and operation timing.
- `--log-file PATH` for persistent INFO/DEBUG troubleshooting logs with
  automatic parent-directory creation.
- Safer installer with dependency aggregation, confirmation prompts, `--yes`,
  `--no-enable`, user-systemd validation, and timestamped config backups.
- Safer uninstaller with confirmation prompts, `--yes`, and optional `--purge`
  removal of configuration and cached frames.
- Opt-in live KDE Plasma integration test that applies a temporary wallpaper,
  verifies every desktop read-back, and restores the previous configuration.
- Manual GitHub Actions workflow for a self-hosted Plasma desktop runner.
- Dedicated installation, troubleshooting, architecture, testing, and release
  process documentation.
- README CI and release badges plus a central documentation index.
- Automated tests, coverage reporting, and Python 3.12 through 3.14 CI.
- Contributor guidance and GitHub issue and pull request templates.
- Validated wheel and source-distribution builds.
- Tag-driven GitHub Release workflow with version and changelog checks.
- Release-candidate tag support for `vX.Y.Z-rcN` GitHub pre-releases.

### Changed

- Primary CLI information actions are mutually exclusive to prevent ambiguous
  command combinations.
- Plasma wallpaper updates verify configuration read-back and emit desktop
  counts and elapsed timing through the application logger.
- Plasma wallpaper application uses unique `.plasma-render` aliases to avoid
  stale renderer-cache reuse.
- Decoded Apple Dynamic Desktop metadata is cached on disk and reused while the
  source HEIC fingerprint remains unchanged, reducing recurring timer-run
  overhead and avoiding unnecessary `exiftool` calls.
- Corrupt or stale metadata caches are ignored and rebuilt automatically.
- Stable `vX.Y.Z` tags publish normal GitHub releases, while matching
  `vX.Y.Z-rcN` tags are marked as pre-releases and do not replace the latest
  stable release.

### Release polish

- Make state and configuration replacement durable with file and directory fsync.
- Expand release validation and packaging documentation.

### Packaging

- Add reproducible Debian package and Arch PKGBUILD tooling.
- Add a GitHub Actions workflow that publishes native-package build artifacts.
