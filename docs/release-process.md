# Release process

The package version in `pyproject.toml` is the release source of truth.

## Release candidates

With package version `0.2.0`, valid tags include:

```text
v0.2.0-rc1
v0.2.0-rc2
v0.2.0-rc10
```

RC tags create GitHub pre-releases and do not replace the latest stable release.

## Stable release

The stable tag must match exactly:

```text
v0.2.0
```

## Checklist

1. Confirm the working tree is clean and the release commit is on the intended
   branch.
2. Run the standard quality checks in `CONTRIBUTING.md`.
3. Run the live Plasma integration workflow when a self-hosted desktop runner
   is available.
4. Move completed entries from `[Unreleased]` into the target version section
   in `CHANGELOG.md`, add the release date, and ensure the section is non-empty.
5. Update `pyproject.toml` when releasing a new package version and confirm its
   development-status classifier is appropriate.
6. Build and validate the distributions locally:

   ```bash
   rm -rf build dist *.egg-info
   python -m build
   python -m twine check dist/*
   ```

7. Commit and push the release preparation.
8. Create an annotated matching tag and push it.
9. Confirm the GitHub release workflow succeeds and that the wheel, source
   archive, and release notes are attached.
10. Install the released wheel in a clean environment and run
    `dynamic-wallpaper --version` as a final smoke test.

Example release candidate:

```bash
git tag -a v0.2.0-rc1 -m "Release v0.2.0-rc1"
git push origin v0.2.0-rc1
```

Example stable release:

```bash
git tag -a v0.2.0 -m "Release v0.1.0"
git push origin v0.2.0
```

The release workflow validates formatting, lint, tests, coverage, distribution
metadata, installed CLI behavior, tag/version agreement, and changelog content
before creating the GitHub release and attaching the wheel and source archive. Stable tags also publish the verified distributions to PyPI through GitHub trusted publishing; release-candidate tags remain GitHub-only pre-releases.


## PyPI trusted publishing setup

Before the first stable release, create a PyPI project or pending publisher for
`plasma-dynamic-wallpaper` and authorize this repository's
`.github/workflows/release.yml` workflow. No long-lived API token is stored in
GitHub. The publish step runs only for stable tags such as `v0.2.0`; RC tags are
never uploaded to PyPI.
