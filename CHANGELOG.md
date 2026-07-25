# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Safer installer with dependency aggregation, confirmation prompts, `--yes`,
  `--no-enable`, user-systemd validation, and timestamped config backups.
- Safer uninstaller with confirmation prompts, `--yes`, and optional `--purge`
  removal of configuration and cached frames.
- Script interface tests for help and invalid options.

### Added

- `dynamic-wallpaper --cache-status` reporting for cache freshness and extracted frame count.
- `dynamic-wallpaper --rebuild-cache` for forced frame re-extraction without manual cache deletion.
- `dynamic-wallpaper --config` output for the active configuration file, HEIC source, and cache directory.
- `dynamic-wallpaper --doctor` readiness checks for dependencies, configuration, wallpaper access, and cache-directory availability.
- `dynamic-wallpaper --status` reporting for the last successfully applied frame, timestamp, and cached wallpaper availability.

### Changed

- Primary CLI information actions are now mutually exclusive to prevent ambiguous command combinations.

## [0.1.0] - 2026-07-24

### Added

- Initial KDE Plasma dynamic HEIC wallpaper implementation.
- Apple `apple_desktop:h24` metadata decoding.
- Frame extraction, caching, scheduling, state tracking, and systemd integration.
- CLI `--version` option and actionable configuration validation.
- Automated tests, coverage reporting, and Python 3.12 through 3.14 CI.
- Contributor guidance and GitHub issue and pull request templates.
- Validated wheel and source-distribution builds.
- Tag-driven GitHub Release workflow with version and changelog checks.
