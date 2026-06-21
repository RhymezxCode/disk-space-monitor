# Changelog

All notable changes to **Disk Space Monitor** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[1.0.0]: https://github.com/RhymezxCode/disk-space-monitor/releases/tag/v1.0.0
