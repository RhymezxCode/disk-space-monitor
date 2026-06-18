# 🖴 Disk Space Monitor

A lightweight **floating, always-on-top widget** for Linux that shows live disk
usage for every real partition — physical drives, mounted Windows/NTFS volumes,
and USB sticks — and updates in **real time** as space grows and shrinks.

It floats above other windows so you can keep an eye on free space while you
work, no matter what app is in front.

```
┌────────────────────────────────────┐
│ ● Disk Monitor            📌 ▭ ✕    │
├────────────────────────────────────┤
│ Root  (/)              ▲ 12 MB  98% │
│ ███████████████████████████████░    │
│ 179.9 GB / 194.4 GB · 4.5 GB free   │
│                                      │
│ /media/windows1                78%  │
│ ████████████████████░░░░░░░░░░       │
│ 215.4 GB / 276.5 GB · 61.2 GB free  │
└────────────────────────────────────┘
```

## ✨ Features

- **Always-on-top overlay** — floats over any window, on any workspace.
- **Real-time updates** — usage refreshes every 0.5–5s with ▲/▼ indicators
  showing how much each drive grew or shrank since the last tick.
- **All real partitions** — auto-filters the noise (snap/`squashfs` loop mounts,
  `tmpfs`, and other pseudo filesystems).
- **Polished UI** — rounded cards, smooth **color-gradient** bars (green →
  yellow → orange → red) with rounded caps, animated fill/percentage
  transitions, per-drive icons (🐧 Linux · 🪟 Windows · 🔌 removable · ⚙ boot),
  a gradient accent header, and a soft fade-in on launch.
- **Frameless & draggable** — drag from anywhere to reposition it.
- **Remembers its place** — position, refresh speed, and view mode persist.
- **Auto-detects USB drives** — plug one in and it appears; unplug and it goes.
- **Zero heavy dependencies** — pure Python (Tkinter, already on most distros)
  plus `psutil`.

---

# 📥 Installation

The app needs three things, all of which are already present on most desktop
Linux installs:

| Requirement | Check it with |
| --- | --- |
| Python 3.8+ | `python3 --version` |
| Tkinter (GUI) | `python3 -c "import tkinter; print('ok')"` |
| psutil (disk stats) | `python3 -c "import psutil; print('ok')"` |

If all three print without error, **skip straight to [Step 2](#step-2--get-the-code)**.

## Step 1 — Install the dependencies

Pick the block for your distribution. (These install Python, Tkinter, and
`psutil` from your system package manager — the cleanest, most reliable route.)

**Debian / Ubuntu / Linux Mint / Pop!\_OS**
```bash
sudo apt update
sudo apt install -y python3 python3-tk python3-psutil
```

**Fedora / RHEL / CentOS Stream**
```bash
sudo dnf install -y python3 python3-tkinter python3-psutil
```

**Arch / Manjaro / EndeavourOS**
```bash
sudo pacman -S --needed python tk python-psutil
```

**openSUSE**
```bash
sudo zypper install -y python3 python3-tk python3-psutil
```

> **Alternatively, install `psutil` with pip** (Tkinter must still come from your
> package manager — it is **not** pip-installable):
> ```bash
> pip install --user psutil
> ```
> On Python 3.11+ you may hit an *“externally-managed-environment”* error
> (PEP 668). See [Troubleshooting](#externally-managed-environment-error) for the
> fix — or just use the system package above.

## Step 2 — Get the code

**Clone with git** (recommended):
```bash
git clone https://github.com/<your-username>/disk-space-monitor.git
cd disk-space-monitor
```

**…or download the ZIP** from the GitHub *Code → Download ZIP* button, then:
```bash
unzip disk-space-monitor-main.zip
cd disk-space-monitor-main
```

## Step 3 — Run it

```bash
python3 disk_monitor.py
```
or use the convenience launcher:
```bash
./run.sh
```

The widget should appear in the top-left of your screen, floating above your
other windows. Drag it wherever you like — it remembers the spot.

---

# 🖥️ Install as a desktop app (optional)

To add **Disk Space Monitor** to your application menu / app grid so you can
launch it like any other app:

```bash
./install.sh
```

This script:
1. Verifies `psutil` is available (and tries to install it if not).
2. Writes a launcher to `~/.local/share/applications/disk-space-monitor.desktop`
   pointing at this folder.

After it runs, search your apps for **“Disk Space Monitor”**.

> ⚠️ **Keep the folder where it is.** The launcher points at the scripts in this
> directory. If you move the folder, re-run `./install.sh`.

## Start automatically at login

Copy the launcher into your autostart folder:
```bash
mkdir -p ~/.config/autostart
cp disk-space-monitor.desktop ~/.config/autostart/
# make the Exec path absolute so it works from anywhere:
sed -i "s|Exec=python3 disk_monitor.py|Exec=python3 $(pwd)/disk_monitor.py|" \
    ~/.config/autostart/disk-space-monitor.desktop
```
On GNOME you can also use the **Startup Applications** tool and point it at
`run.sh`.

---

# 🧪 Isolated install with a virtual environment (advanced)

Prefer not to touch system packages? Use a venv. Note that Tkinter still has to
come from the system (`python3-tk`), but `psutil` lives in the venv:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python disk_monitor.py
```
To run later: `source .venv/bin/activate && python disk_monitor.py`.

---

# 🎮 Controls

| Action | How |
| --- | --- |
| Move the widget | Click & drag anywhere on it |
| Open a drive in your file manager | Double-click its row |
| Options menu | Right-click anywhere |
| Toggle always-on-top | 📌 button (or right-click menu) |
| Compact view (hide details) | ▭ button (or right-click menu) |
| Change update speed (0.5s–5s) | Right-click → *Update speed* |
| Close | ✕ button (or right-click → *Quit*) |

---

# ⚙️ Configuration

Settings persist automatically to:
```
~/.config/disk-space-monitor/config.json
```
It stores window position (`x`, `y`), refresh interval (`interval_ms`),
always-on-top state (`pinned`), and compact mode (`compact`). **Delete this file
to reset to defaults.**

To change colours, default size, fill thresholds, or which filesystems are
hidden, edit the constants near the top of `disk_monitor.py`.

---

# 🩹 Troubleshooting

### `ModuleNotFoundError: No module named 'psutil'`
Install it: `sudo apt install python3-psutil` (or your distro’s equivalent from
[Step 1](#step-1--install-the-dependencies)), or `pip install --user psutil`.

### `ModuleNotFoundError: No module named 'tkinter'` / `_tkinter`
Tkinter isn’t bundled in some minimal Python installs. Install the system
package: `python3-tk` (Debian/Ubuntu), `python3-tkinter` (Fedora), `tk` (Arch).
It is **not** available via pip.

### `externally-managed-environment` error
Modern distros (PEP 668) block `pip install` into system Python. Best fix:
install `psutil` from your package manager instead (`sudo apt install
python3-psutil`). If you must use pip, either use a
[virtual environment](#-isolated-install-with-a-virtual-environment-advanced) or
override:
```bash
pip install --user --break-system-packages psutil
```

### The window doesn’t stay on top / appears behind other windows
- **Wayland (GNOME/KDE):** the app runs through XWayland, where always-on-top
  works. Make sure XWayland is available — `echo $DISPLAY` should print
  something like `:0`. (Pure-Wayland sessions without XWayland can’t honor
  always-on-top for any app.)
- Toggle the 📌 button off and on, or pick *Toggle always-on-top* from the
  right-click menu.
- A few tiling window managers ignore the always-on-top hint; consult your WM’s
  floating-window rules.

### `Authorization required` / `cannot connect to display`
Run it from inside your graphical desktop session (a normal terminal), not over
plain SSH. For SSH use `ssh -X` (X11 forwarding).

### A drive I expected isn’t shown
By design the app hides snap/`squashfs`, `tmpfs`, and other pseudo filesystems.
Network shares or unusual filesystem types may also be filtered — see the
`SKIP_FSTYPES` / `SKIP_PREFIXES` constants in `disk_monitor.py` to adjust.

### A drive shows but usage looks wrong / permission denied
Some FUSE mounts (e.g. certain NTFS configs) restrict `statvfs`. The app skips
partitions it can’t read rather than crashing.

---

# 🗑️ Uninstall

```bash
# remove the app launcher (if you ran install.sh)
rm -f ~/.local/share/applications/disk-space-monitor.desktop
rm -f ~/.config/autostart/disk-space-monitor.desktop

# remove saved settings
rm -rf ~/.config/disk-space-monitor

# remove the code
cd .. && rm -rf disk-space-monitor
```
System packages (`python3-tk`, `python3-psutil`) are shared and safe to leave
installed; remove them with your package manager only if nothing else needs them.

---

# 🛠️ How it works

`psutil.disk_partitions()` enumerates mounts; pseudo/loop filesystems are
filtered out by type and mount-point prefix. `psutil.disk_usage()` reads
total/used/free for each remaining partition once per tick. The UI is a
frameless Tkinter window with `overrideredirect` + `-topmost`, redrawn on a
`Tk.after()` timer — single-threaded, no busy-waiting.

# 🤝 Contributing

Issues and pull requests welcome! Ideas: per-drive read/write throughput, a
system-tray icon, configurable warning thresholds with desktop notifications,
and theming presets.

# 📄 License

[MIT](LICENSE) — do whatever you like; attribution appreciated.
