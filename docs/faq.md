# Frequently asked questions

## Does the project modify my HEIC file?

No. The source file is read-only. Extracted PNG frames, decoded metadata, render
aliases, and state are stored below the configured cache directory.

## Does it require root access?

Normal use does not. The installer creates user configuration and user-level
systemd units. Native distribution packages may require administrator access to
install the global command, after which each user runs `dynamic-wallpaper --setup`.

## Why does the timer run every minute?

The operation is normally cache-only and lightweight. The short interval also
bounds recovery time after a display-layout change or a missed Plasma update.
State reconciliation prevents unnecessary wallpaper writes.

## Why is there a watchdog in addition to the timer?

The watchdog responds immediately when Plasma Shell returns on D-Bus or the
system resumes. The timer remains a simple fallback and regular reconciliation
mechanism.

## Why does Plasma show an inactive `screen=-1` desktop?

Plasma may retain a containment for a disconnected display. The application
ignores inactive containments and updates them when Plasma assigns an active
screen again.

## Does solar mode contact a geocoding service?

No. Solar calculations are local and use the latitude and longitude supplied in
the configuration. Optional automatic location discovery may be considered in a
future release with explicit user consent.

## Can different monitors use different HEIC wallpapers?

Not yet. The current multi-monitor support applies the selected wallpaper to all
active target screens. Per-monitor wallpaper selection is a future feature.

## Why are unique `.plasma-render` files created?

Plasma can retain an old texture when the same path is reused. Unique aliases
provide a new URI while avoiding duplicate image data where hard links are
available. Cleanup protects aliases still referenced by active desktops.
