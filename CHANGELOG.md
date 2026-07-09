# Changelog

All notable changes to **Disk Space Monitor** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-07-09

A window-controls and features release: the widget now behaves more like a
normal window (minimize, maximize) and gains disk alerts, live I/O throughput,
a light theme, and a largest-items scanner.

### Added

- **Minimize button** (`—`) in the header — because the widget is borderless it
  briefly hands itself back to the window manager so it lands in the **taskbar**;
  restore it from the taskbar and the custom chrome is re-applied automatically.
- **Maximize / restore button** (`▢` ⇄ `❐`) — expands to fill the **current
  monitor's** work area (multi-monitor aware, respects panels) and reflows the
  partition cards into a responsive **multi-column grid**; click again to restore
  the previous size and position.
- **Disk-full desktop alerts** — a `notify-send` warning when any disk crosses a
  configurable threshold (default 90%), with hysteresis so it fires once rather
  than every refresh. Toggle + threshold slider in Settings.
- **Live disk I/O** — per-partition read/write throughput (`↓ … ↑ …`) via
  `psutil.disk_io_counters`, shown on each card. Toggle in Settings.
- **Light / dark theme** — a new light palette and a toggle (header menu or
  Settings); the choice is persisted.
- **Largest files/folders scan** — *right-click a partition → Find largest items
  here…* runs `du` on a background thread (never freezes the UI) and lists the
  biggest items; click a row to open its location.
- **Copy usage report** — copies a plain-text summary of every partition to the
  clipboard (right-click menu).
- **Pause / resume updates** — freeze/thaw the refresh loop from the menu or
  Settings; a `⏸` appears in the title while paused.

### Changed

- The header now carries **`—`** (minimize) and **`▢`** (maximize) alongside the
  existing ⚙ 📌 ▭ ✕ buttons; normal cards are slightly taller to fit the I/O line.
- `config.json` now also persists **theme**, **alerts_enabled**, **alert_threshold**
  and **show_io**.
- Card placement moved from `pack` to a single grid-based layout path, enabling
  the maximized multi-column view.

### Fixed

- Toggling compact view (and now theme switches) no longer risk spawning extra
  refresh loops — the periodic tick is now separate from the one-shot update.

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
