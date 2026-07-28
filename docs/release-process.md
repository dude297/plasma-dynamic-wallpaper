# Release process

The package version in `pyproject.toml` is the release source of truth.

## Release candidates

With package version `0.1.0`, valid tags include:

```text
v0.1.0-rc1
v0.1.0-rc2
v0.1.0-rc10
```

RC tags create GitHub pre-releases and do not replace the latest stable release.

## Stable release

The stable tag must match exactly:

```text
v0.1.0
```

## Checklist

1. Run the standard quality checks in `CONTRIBUTING.md`.
2. Run the live Plasma integration workflow when a self-hosted desktop runner
   is available.
3. Update `CHANGELOG.md` and ensure the target version section is non-empty.
4. Update `pyproject.toml` when releasing a new package version.
5. Commit and push the release preparation.
6. Create an annotated matching tag and push it.

Example release candidate:

```bash
git tag -a v0.1.0-rc6 -m "Release v0.1.0-rc6"
git push origin v0.1.0-rc6
```

Example stable release:

```bash
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0
```

The release workflow validates formatting, lint, tests, coverage, distribution
metadata, installed CLI behavior, tag/version agreement, and changelog content
before creating the GitHub release and attaching the wheel and source archive.
