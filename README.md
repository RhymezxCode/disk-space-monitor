# 🖴 Disk Space Monitor

A lightweight **floating, always-on-top widget** for Linux that shows live disk
usage for every real partition — physical drives, mounted Windows/NTFS volumes,
and USB sticks — and updates in **real time** as space grows and shrinks.

It floats above other windows so you can keep an eye on free space while you
work, no matter what app is in front.

```
┌──────────────────────────────┐
│ ● Disk Monitor      📌 ▭ ✕   │
├──────────────────────────────┤
│ Root  (/)            ▲ 12 MB  98% │
│ ███████████████████████████░  │
│ 179.9 GB / 194.4 GB · 4.5 GB free │
│                                │
│ /media/windows1          78%   │
│ ██████████████████░░░░░░░░░░░  │
│ 215.4 GB / 276.5 GB · 61.2 GB free│
└──────────────────────────────┘
```

## ✨ Features

- **Always-on-top overlay** — floats over any window, on any workspace.
- **Real-time updates** — usage refreshes on an interval (0.5s–5s) with a
  ▲/▼ indicator showing how much each drive grew or shrank since the last tick.
- **All real partitions** — automatically filters out the noise (snap/`squashfs`
  loop mounts, `tmpfs`, and other pseudo filesystems).
- **Color-coded bars** — green → yellow → orange → red as a drive fills up.
- **Frameless & draggable** — drag from anywhere on the widget to reposition it.
- **Remembers its place** — position, refresh speed, and view mode persist.
- **Auto-detects USB drives** — plug one in and it appears; unplug and it goes.
- **Zero heavy dependencies** — pure Python (Tkinter, already on most distros)
  plus `psutil`.

## 📦 Requirements

- Linux with Python 3.8+
- **Tkinter** — usually preinstalled. If not: `sudo apt install python3-tk`
- **psutil** — `pip install psutil` (or `sudo apt install python3-psutil`)

> **Wayland note:** Tkinter renders through XWayland, so the always-on-top and
> overlay behaviour works correctly on GNOME/KDE Wayland sessions as well as
> X11. No configuration needed.

## 🚀 Quick start

```bash
git clone https://github.com/<your-username>/disk-space-monitor.git
cd disk-space-monitor

# install dependency (skip if psutil is already present)
pip install -r requirements.txt

# run it
python3 disk_monitor.py
#   …or
./run.sh
```

### Install as a desktop app (optional)

Adds a "Disk Space Monitor" entry to your app grid:

```bash
./install.sh
```

To launch it automatically at login, add the same launcher to GNOME's
*Startup Applications* (or copy `disk-space-monitor.desktop` to
`~/.config/autostart/`).

## 🎮 Controls

| Action | How |
| --- | --- |
| Move the widget | Click & drag anywhere on it |
| Open a drive in your file manager | Double-click its row |
| Options menu | Right-click anywhere |
| Toggle always-on-top | 📌 button (or right-click menu) |
| Compact view (hide details) | ▭ button (or right-click menu) |
| Change update speed | Right-click → *Update speed* |
| Close | ✕ button (or right-click → *Quit*) |

## ⚙️ Configuration

Settings persist automatically to:

```
~/.config/disk-space-monitor/config.json
```

It stores the window position (`x`, `y`), refresh interval (`interval_ms`),
always-on-top state (`pinned`), and compact mode (`compact`). Delete the file
to reset to defaults.

You can also tweak the theme colours, default size, and thresholds by editing
the constants at the top of `disk_monitor.py`.

## 🛠️ How it works

`psutil.disk_partitions()` enumerates mounts; pseudo/loop filesystems are
filtered out by type and mount-point prefix. `psutil.disk_usage()` reads
total/used/free for each remaining partition once per tick. The UI is a
frameless Tkinter window with `overrideredirect` + `-topmost`, redrawn on a
`Tk.after()` timer — single-threaded, no busy-waiting.

## 🤝 Contributing

Issues and pull requests are welcome! Ideas: per-drive read/write throughput,
a system-tray icon, a configurable warning threshold with desktop
notifications, theming presets.

## 📄 License

[MIT](LICENSE) — do whatever you like; attribution appreciated.
