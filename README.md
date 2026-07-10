# 🖴 Disk Space Monitor

A lightweight **floating, always-on-top widget** for Linux that shows live disk
usage for every real partition — physical drives, mounted Windows/NTFS volumes,
and USB sticks — and updates in **real time** as space grows and shrinks.

It floats above other windows so you can keep an eye on free space while you
work, no matter what app is in front.

```
┌──────────────────────────────────────┐
│ 💽 Disk Monitor      ⚙ 📌 ▭ — ▢ ✕   │
├──────────────────────────────────────┤
│ 🐧 Root  (/)          ▲ 12 MB   94%  │
│ ██████████████████████████████░░      │
│ 179.9 GB / 194.4 GB · 11.3 GB free   │
│ ↓ 2.1 MB/s      ↑ 0.4 MB/s           │
│                                      │
│ 🪟 /media/windows1               78%  │
│ ████████████████████░░░░░░░░░░        │
│ 215.4 GB / 276.5 GB · 61.2 GB free   │
│ ↓ 0 B/s         ↑ 0 B/s              │
└──────────────────────────────────────┘
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
- **Window controls** — **minimize** (`—`) hides the widget to the taskbar like
  any normal window (double-click the header does the same; restore it from the
  dock or Alt-Tab), and **maximize** (`▢`) fills the current monitor, right where
  you'd expect them in the top-right. Maximizing reflows the cards into a
  responsive multi-column grid.
- **Disk-full alerts** — get a desktop notification when a disk crosses a
  threshold you choose (default 90%). Only your root filesystem (`/`) is watched
  by default; flip one setting to watch every partition.
- **Live disk I/O** — see per-drive read/write throughput (`↓ … ↑ …`), not just
  space.
- **Light & dark themes** — pick the look you like; the choice is remembered.
- **Find what's eating space** — right-click a drive → **Find largest items
  here…** to scan and list the biggest files/folders (runs in the background).
- **Copy usage report** — grab a plain-text summary of every drive to your
  clipboard from the right-click menu.
- **Pause / resume** — freeze updates whenever you like.
- **Resizable** — drag the corner grip (or the Width slider in Settings) to size
  it to your taste; the width is remembered.
- **Settings panel** (⚙) — a polished dialog with everything in one place:
  start-on-login, always-on-top, compact view, theme, alerts, disk I/O, refresh
  interval, opacity, width, maximize/restore, reset position, open settings
  folder, and a one-click **Uninstall**.
- **Start on login** — flip one switch to launch the widget automatically at
  every login (writes/removes a `~/.config/autostart` entry for you).
- **Remembers its place** — position, size, opacity, refresh speed, and view
  mode all persist.
- **Multi-monitor aware** — maximize fills the monitor the widget is actually on,
  and a position saved on a display you've since unplugged won't strand it
  off-screen.
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
git clone https://github.com/RhymezxCode/disk-space-monitor.git
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

The widget should appear near the top-left of your primary monitor, floating
above your other windows. Drag it wherever you like — it remembers the spot.

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

The easiest way: open **Settings** (⚙ in the header) and turn on
**Start on login**. That writes a correct, absolute-path autostart entry to
`~/.config/autostart/disk-space-monitor.desktop` for you — turn the switch back
off to remove it.

Prefer to do it by hand?
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
| Resize the widget | Drag the grip in the bottom-right corner |
| Minimize to the taskbar | `—` button (or double-click the header) |
| Maximize / restore | `▢` button (fills the current monitor) |
| Open Settings | ⚙ button (or right-click → *Settings…*) |
| Open a drive in your file manager | Double-click its row |
| Find largest files/folders | Right-click a drive → *Find largest items here…* |
| Copy a usage report | Right-click → *Copy usage report* |
| Pause / resume updates | Right-click → *Pause / resume updates* |
| Switch light / dark theme | Right-click → *Switch light / dark theme* (or Settings) |
| Options menu | Right-click anywhere |
| Toggle always-on-top | 📌 button (or Settings / right-click menu) |
| Compact view (hide details) | ▭ button (or Settings / right-click menu) |
| Change update speed (0.5s–5s) | Settings, or right-click → *Update speed* |
| Close | ✕ button (or right-click → *Quit*) |

---

# 🎛️ Settings

Click the ⚙ button (or right-click → *Settings…*) to open the Settings panel:

| Setting | What it does |
| --- | --- |
| **Start on login** | Launch the widget automatically every login (toggles the `~/.config/autostart` entry) |
| **Always on top** | Keep the widget floating above other windows |
| **Compact view** | Hide the size/free details for a slimmer widget |
| **Pause updates** | Freeze the refresh loop (a `⏸` shows in the title) |
| **Show disk I/O speeds** | Show per-drive read/write throughput on each card |
| **Disk-full desktop alerts** | Notify when a disk crosses the threshold below |
| **Only alert for root (/)** | Ignore secondary mounts, which often sit near-full (on by default) |
| **Alert threshold (%)** | The usage level that triggers an alert, 50 – 99 |
| **Light theme** | Switch between the dark and light palettes |
| **Refresh interval** | How often usage is re-read, 0.3s – 5s |
| **Opacity** | Window transparency, 0.3 – 1.0 (applies live) |
| **Width** | Widget width, 280 – 760 px (applies live; same as the corner grip) |
| **Maximize / restore** | Fill the current monitor, or return to the previous size |
| **Reset position** | Snap the widget back to the top-left of the primary monitor |
| **Open settings folder** | Open `~/.config/disk-space-monitor` in your file manager |
| **Uninstall Disk Monitor…** | Remove the launcher, autostart entry and saved settings, then close (asks first; leaves the program files) |

---

# ⚙️ Configuration

Settings persist automatically to:
```
~/.config/disk-space-monitor/config.json
```
It stores window position (`x`, `y`), size (`width`), opacity (`alpha`), refresh
interval (`interval_ms`), always-on-top state (`pinned`), compact mode
(`compact`), the `theme`, disk-alert settings (`alerts_enabled`,
`alert_threshold`, `alert_root_only`), and whether disk I/O is shown (`show_io`).
**Delete this file to reset to defaults.**

The saved position is validated against your connected monitors at startup, so a
position saved on a display you've since unplugged won't strand the widget
off-screen — it reappears on your primary monitor instead.

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

### The app starts but no window appears
Since v1.1.2 the saved position is validated against your connected monitors, so
this shouldn’t happen — but if a window is ever missing while the process is
running, check for orphaned copies and clear them:
```bash
pgrep -af disk_monitor.py          # is it actually running?
pkill -f disk_monitor.py           # stop every copy
rm -f ~/.config/disk-space-monitor/config.json   # last resort: reset position
```
On older versions, coordinates saved on an external display would place the
widget off-screen after you unplugged that display: it ran, but was never
visible.

### Minimize hides the widget and I can’t get it back
Restore it from your dock or with **Alt-Tab** — minimize (`—`) is a real window
minimize. If it isn’t in either place, your window manager likely ignores
`_MOTIF_WM_HINTS`; the app then falls back to collapsing the widget to its title
bar instead, and `—` toggles it back.

### The dock/taskbar shows a blank square instead of the disk icon
Your desktop entry is missing `StartupWMClass=Disk-space-monitor`, which is how
the shell pairs the window with the launcher. Re-run `./install.sh`, then log out
and back in (GNOME caches desktop entries).

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

**Easiest:** open **Settings** (⚙) → **Uninstall Disk Monitor…**. It asks for
confirmation, then removes the launcher, the autostart entry and your saved
settings, and closes. (It intentionally leaves the program files so you can
delete the folder yourself.)

**From a terminal:** run the bundled script —
```bash
./uninstall.sh
```
which does the same launcher/autostart/settings cleanup.

**By hand**, if you prefer:
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
total/used/free for each remaining partition once per tick, and
`psutil.disk_io_counters(perdisk=True)` gives the throughput figures, differenced
against the previous tick.

The UI is a Tkinter window redrawn on a `Tk.after()` timer, with `-topmost` for
the always-on-top behaviour. It has no title bar, but it is **not**
`overrideredirect`: that hides decorations by unmanaging the window entirely,
which costs it a taskbar button and makes `iconify()` a no-op. Instead it asks
the window manager for zero decorations via `_MOTIF_WM_HINTS`, so it stays
managed and `—` performs a real minimize. The hint is set on Tk's *wrapper*
window — `winfo_id()` returns the inner window, whose properties the WM ignores.
Window managers that ignore the hint fall back to `overrideredirect`, where `—`
collapses the widget to its title bar instead.

The saved position is checked against the currently connected monitors before
it's reused, so unplugging a display can't strand the widget off-screen.

Everything runs on the Tk main loop — no busy-waiting — except the *Find largest
items* scan, which shells out to `du` on a background thread and posts its result
back with `root.after()`, since Tk is not thread-safe.

# 🤝 Contributing

Issues and pull requests welcome! Ideas: a system-tray icon, custom theme
presets beyond light/dark, per-drive alert thresholds, a native Wayland backend
(the widget currently relies on XWayland), and SMART health readouts.

# 📄 License

[MIT](LICENSE) — do whatever you like; attribution appreciated.
