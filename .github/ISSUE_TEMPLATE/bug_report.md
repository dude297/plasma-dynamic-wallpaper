---
name: Bug report
about: Report reproducible incorrect behavior
title: "[Bug] "
labels: bug
assignees: ""
---

## Description

Describe what happened and what you expected instead.

## Steps to reproduce

1.
2.
3.

## Environment

- Distribution and version:
- KDE Plasma version:
- Session type (Wayland/X11):
- Python version:
- Project version (`dynamic-wallpaper --version`):
- Installation method (`pipx`, source, Debian, Arch, other):
- Number of active displays:

## Diagnostics

Run and include the relevant output:

```bash
dynamic-wallpaper --doctor
dynamic-wallpaper --current
systemctl --user status dynamic-wallpaper.timer --no-pager -l
systemctl --user status dynamic-wallpaper-watch.service --no-pager -l
journalctl --user -u dynamic-wallpaper.service -n 50 --no-pager
```

For timing, cache, or Plasma verification problems, also include:

```bash
dynamic-wallpaper --force --verbose
```

## Privacy checklist

- [ ] I removed access tokens and unrelated personal information.
- [ ] I redacted private home paths, coordinates, and wallpaper names if needed.
- [ ] This report does not contain a security vulnerability; those are reported privately.

## Additional context

Add screenshots or other context. Do not upload copyrighted wallpaper files
unless you have permission to share them.
