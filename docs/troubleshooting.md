# Troubleshooting

## Start with diagnostics

Run:

```bash
dynamic-wallpaper --doctor
dynamic-wallpaper --config
dynamic-wallpaper --cache-status
dynamic-wallpaper --status
```

For a complete operation trace:

```bash
dynamic-wallpaper --force --verbose
```

To retain logs:

```bash
dynamic-wallpaper --force --verbose \
  --log-file "$HOME/.cache/dynamic-wallpaper/debug.log"
```

## The command works but the desktop does not change

Confirm Plasma retained the requested image:

```bash
qdbus6 org.kde.plasmashell /PlasmaShell \
  org.kde.PlasmaShell.evaluateScript '
for (const d of desktops()) {
    d.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
    print(d.readConfig("Image", "<missing>"));
}'
```

A recent application should point to a unique file under `.plasma-render`.
The alias exists to avoid stale renderer-cache behavior. If read-back is
correct but the visible desktop remains stale, record the verbose log and the
Plasma version before restarting `plasmashell`; the mismatch is then in the
live Plasma renderer rather than the configuration write.

## First run is slow

The first run extracts HEIC frames and decodes metadata. Later runs reuse both
caches while the source file fingerprint is unchanged. A typical cached run
should complete in milliseconds rather than seconds.

Use this command to inspect the cache:

```bash
dynamic-wallpaper --cache-status
```

Rebuild it only when necessary:

```bash
dynamic-wallpaper --rebuild-cache
```

## Timer does not run

```bash
systemctl --user status dynamic-wallpaper.timer
systemctl --user status dynamic-wallpaper.service
journalctl --user -u dynamic-wallpaper.service -n 100
```

The service must run as the logged-in Plasma user so that it inherits access to
the desktop D-Bus session.

## Missing dependency

```bash
command -v exiftool
command -v heif-convert
command -v qdbus6
```

On Ubuntu or Kubuntu:

```bash
sudo apt install libimage-exiftool-perl libheif-examples qdbus-qt6
```

## Configuration errors

Inspect resolved paths:

```bash
dynamic-wallpaper --config
```

Verify the HEIC file exists and that the cache parent directory is writable.
Use `config/config.example` as the reference format.

## Collecting a useful bug report

Include:

```bash
dynamic-wallpaper --version
plasmashell --version
python --version
dynamic-wallpaper --doctor
dynamic-wallpaper --force --verbose
systemctl --user status dynamic-wallpaper.timer
journalctl --user -u dynamic-wallpaper.service -n 100
```

Do not include private filesystem paths or wallpaper files unless they are
necessary to reproduce the issue.


## Multi-monitor service reports an invalid verification response

Older development builds printed one JSON object per Plasma desktop. Plasma
can concatenate those objects without newlines, causing the user service to
exit even though every screen accepted the wallpaper. Upgrade to a build that
uses a single verification payload, then reset and test the service:

```bash
systemctl --user reset-failed dynamic-wallpaper.service
systemctl --user start dynamic-wallpaper.service
systemctl --user status dynamic-wallpaper.service --no-pager
```

A successful oneshot finishes as inactive with a successful result.

## Plasma points to a missing `.plasma-render` file

Current builds protect all wallpaper aliases referenced by any desktop before
pruning inactive aliases. To recover an older installation, stop the timer,
apply a persistent extracted frame, upgrade, and then restart the timer.

```bash
systemctl --user stop dynamic-wallpaper.timer
dynamic-wallpaper --force
systemctl --user start dynamic-wallpaper.timer
```

## Wallpaper is not calibrated immediately after login

Current systemd units invoke `dynamic-wallpaper --startup`. That mode waits up
to 45 seconds for Plasma's D-Bus service and at least one active desktop
containment, then reads the current time and force-applies the matching frame.
It does not depend on a fixed sleep, so slower login sessions and shell restarts
are handled consistently.

Reinstall the user units after upgrading an older setup:

```bash
dynamic-wallpaper --setup
systemctl --user daemon-reload
systemctl --user restart dynamic-wallpaper.timer
```

Test the startup path directly with:

```bash
dynamic-wallpaper --startup --verbose
```

If it times out, inspect Plasma and the service journal rather than increasing
the timer delay:

```bash
systemctl --user status plasma-plasmashell.service
journalctl --user -u dynamic-wallpaper.service -n 100 --no-pager
```
