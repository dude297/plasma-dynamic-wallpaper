# Support

Use the repository's issue templates for reproducible bugs and feature
requests. Before opening a bug:

```bash
dynamic-wallpaper --version
dynamic-wallpaper --doctor
dynamic-wallpaper --current
systemctl --user status dynamic-wallpaper.timer --no-pager
systemctl --user status dynamic-wallpaper-watch.service --no-pager
```

Include relevant output, but redact usernames, home paths, coordinates, and
private wallpaper filenames when necessary. General installation and runtime
answers are documented in:

- [Installation](docs/installation.md)
- [Troubleshooting](docs/troubleshooting.md)
- [FAQ](docs/faq.md)

Security-sensitive reports must follow [SECURITY.md](SECURITY.md), not a public
issue.
