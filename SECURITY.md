# Security policy

## Supported versions

Security fixes are applied to the latest released version and the current
primary development branch.

## Reporting a vulnerability

Please do not open a public issue for a vulnerability that could expose user
files, execute unintended commands, bypass package verification, or compromise
the desktop session.

Use GitHub's private security-advisory reporting feature for this repository.
Include:

- affected version or commit;
- installation method and Linux distribution;
- reproduction steps or a minimal proof of concept;
- expected and observed impact;
- any suggested mitigation.

You should receive an acknowledgement within seven days. The maintainers will
coordinate validation, a fix, and disclosure timing. Do not include private
wallpaper files, access tokens, home-directory contents, or unrelated logs.

## Scope

High-value areas include:

- HEIC metadata and external-process handling;
- archive and wallpaper-library installation;
- filesystem permissions and atomic writes;
- D-Bus scripts sent to Plasma Shell;
- systemd user-service installation;
- release and package-publishing workflows.
