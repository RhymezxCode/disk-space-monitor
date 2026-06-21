# Changelog

All notable changes to **Disk Space Monitor** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2026-06-21

A usability release that brings every option into one place, makes the widget
resizable, and adds proper desktop integration (start-on-login and a one-click
uninstall).

### Added

- **Settings panel** — a dark-themed dialog opened from a new ⚙ header button or
  *right-click → Settings…*, gathering every preference in one place.
- **Resizable widget** — drag the new grip in the bottom-right corner, or use the
  **Width** slider in Settings (280–760 px). Cards reflow live and the chosen
  width is remembered.
- **Start on login** — a toggle that writes/removes a `~/.config/autostart`
  entry (with an absolute `Exec` path) so the widget can launch at every login.
- **Opacity control** — a slider to set window transparency (0.3–1.0), applied
  live and persisted.
- **In-app uninstall** — *Settings → Uninstall Disk Monitor…* removes the
  launcher, autostart entry, and saved settings after a confirmation, then exits
  (program files are intentionally left in place). A matching `uninstall.sh`
  companion script does the same cleanup from a terminal.
- **Window actions** in Settings — *Reset position* and *Open settings folder*.
- **Version label** shown at the bottom of the Settings panel.

### Changed

- The right-click menu now includes a **Settings…** entry, and the header now
  carries a **⚙** button alongside 📌 (pin), ▭ (compact), and ✕ (close).
- `config.json` now also persists window **width** and **opacity** (`alpha`)
  in addition to position, refresh interval, pinned, and compact state.

### Fixed

- The bundled `disk-space-monitor.desktop` / autostart entries now use the
  Python interpreter and an absolute script path resolved at runtime, so the
  launcher keeps working regardless of where the folder lives.

## [1.0.0] - 2026-06-21

First stable release — a lightweight, floating, always-on-top disk usage widget
for Linux that tracks every real partition in real time.

### Added

#### Monitoring
- **Real-time usage tracking** for all real partitions, refreshed on a
  configurable timer with **▲/▼ trend indicators** showing how much each drive
  grew or shrank since the previous tick.
- **Automatic partition detection** via `psutil`, covering physical drives,
  mounted Windows/NTFS volumes, and removable USB sticks.
- **Live USB hot-plug support** — drives appear when plugged in and disappear
  when removed, with no restart needed.
- **Smart filtering** of pseudo filesystems (snap/`squashfs` loop mounts,
  `tmpfs`, and similar) via the `SKIP_FSTYPES` / `SKIP_PREFIXES` constants.
- **Graceful degradation** — partitions that can't be read (e.g. restrictive
  FUSE/NTFS mounts) are skipped instead of crashing the app.

#### Interface
- **Always-on-top, frameless overlay** that floats above any window on any
  workspace, draggable from anywhere on its surface.
- **Polished card-based UI** with rounded cards, smooth **color-gradient** usage
  bars (green → yellow → orange → red) with rounded caps, and animated
  fill/percentage transitions.
- **Per-drive icons** — 🐧 Linux · 🪟 Windows · 🔌 removable · ⚙ boot — plus a
  gradient accent header and a soft fade-in on launch.
- **Compact view** to collapse per-drive details into a minimal footprint.
- **Adjustable refresh speed** from 0.5s to 5s via the right-click menu.
- **Quick actions** — double-click a drive row to open it in your file manager;
  right-click anywhere for the full options menu.

#### Persistence & integration
- **Settings persistence** to `~/.config/disk-space-monitor/config.json` —
  remembers window position, refresh interval, always-on-top state, and compact
  mode across restarts.
- **Desktop launcher** (`disk-space-monitor.desktop`) and `install.sh` to add
  the app to your application menu / app grid.
- **Convenience launcher** script (`run.sh`) for one-command startup.
- **Autostart-at-login** support documented for GNOME and freedesktop autostart.

#### Project
- **Comprehensive installation guide** in the README covering Debian/Ubuntu,
  Fedora/RHEL, Arch, and openSUSE, plus pip and virtual-environment routes.
- **Troubleshooting section** for common issues (missing `psutil`/`tkinter`,
  PEP 668 externally-managed environments, Wayland always-on-top, display/SSH).
- **Minimal dependencies** — pure Python with Tkinter plus `psutil>=5.9`.
- **MIT licensed.**

[1.0.1]: https://github.com/RhymezxCode/disk-space-monitor/releases/tag/v1.0.1
[1.0.0]: https://github.com/RhymezxCode/disk-space-monitor/releases/tag/v1.0.0
