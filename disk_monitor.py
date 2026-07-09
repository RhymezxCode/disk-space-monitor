#!/usr/bin/env python3
"""
Disk Space Monitor — a floating, always-on-top overlay widget for Linux.

Shows live used/free space for every real partition (physical disks, mounted
Windows/NTFS drives, USB sticks) and updates in real time as space grows and
shrinks. Snap/loop/pseudo filesystems are filtered out automatically.

Built with Tkinter + psutil so it runs with no GUI dependencies to install.
On Wayland it renders through XWayland, which lets the always-on-top and
overlay behaviour work reliably on GNOME.

License: MIT
"""

from __future__ import annotations

__version__ = "1.1.0"

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
from dataclasses import dataclass
from tkinter import messagebox

import psutil

# --------------------------------------------------------------------------- #
# Theme                                                                        #
# --------------------------------------------------------------------------- #
# Two palettes. The dark values are the original theme, unchanged; light is new.
THEMES = {
    "dark": {
        "BG": "#16171f", "CARD": "#23252f", "CARD_HOVER": "#2a2d39",
        "HEADER_BG": "#1b1c24", "BORDER": "#333645", "FG": "#f4f5fb",
        "MUTED": "#8b90a6", "TRACK": "#3a3d4d", "ACCENT": "#bd93f9",
        "DANGER": "#ff6b6b",
    },
    "light": {
        "BG": "#eef0f6", "CARD": "#ffffff", "CARD_HOVER": "#f4f6fb",
        "HEADER_BG": "#e2e5ef", "BORDER": "#c9cede", "FG": "#1c1e26",
        "MUTED": "#6b7186", "TRACK": "#d5d9e6", "ACCENT": "#7c3aed",
        "DANGER": "#e5484d",
    },
}

# Active palette. These module-level names are populated by apply_palette() so
# every existing `BG`, `CARD`, … reference keeps working. Switching theme
# reassigns them and the app rebuilds its widgets (colours are baked in at
# widget-creation time, so a rebuild is required for a live switch).
BG = CARD = CARD_HOVER = HEADER_BG = BORDER = FG = MUTED = TRACK = ACCENT = DANGER = ""


def apply_palette(name: str) -> str:
    """Set the module-level colour globals from THEMES. Returns the theme used."""
    name = name if name in THEMES else "dark"
    pal = THEMES[name]
    global BG, CARD, CARD_HOVER, HEADER_BG, BORDER, FG, MUTED, TRACK, ACCENT, DANGER
    BG, CARD, CARD_HOVER = pal["BG"], pal["CARD"], pal["CARD_HOVER"]
    HEADER_BG, BORDER, FG = pal["HEADER_BG"], pal["BORDER"], pal["FG"]
    MUTED, TRACK, ACCENT, DANGER = pal["MUTED"], pal["TRACK"], pal["ACCENT"], pal["DANGER"]
    return name


apply_palette("dark")

# Smooth usage gradient (green → lime → yellow → orange → red)
USAGE_STOPS = [
    (0.00, (61, 220, 132)),
    (0.45, (155, 229, 63)),
    (0.70, (241, 250, 76)),
    (0.85, (255, 184, 108)),
    (1.00, (255, 85, 85)),
]
# Header accent line (cyan → purple → pink)
HEADER_STOPS = [
    (0.0, (139, 233, 253)),
    (0.5, (189, 147, 249)),
    (1.0, (255, 121, 198)),
]

ALPHA = 0.96            # default window opacity (0..1)
DEFAULT_WIDTH = 348     # default widget width in px
MIN_WIDTH = 280         # smallest the user can shrink the widget
MAX_WIDTH = 760         # largest the user can grow the widget
MIN_CARD = 300          # min card width when reflowing into a grid (maximized)
PAD = 12                # window inner padding
CARD_GAP = 9            # gap between cards
CARD_H = 92             # normal card height (fits the I/O readout line)
CARD_H_COMPACT = 50     # compact card height
HEADER_H = 42
BAR_THICK = 10          # progress bar thickness
RADIUS = 16             # card corner radius

DEFAULT_INTERVAL_MS = 1500   # data refresh cadence
ANIM_MS = 33                 # ~30 fps animation tick
DEFAULT_ALERT_PCT = 90       # warn when a disk is at/above this %
ALERT_HYSTERESIS = 5         # re-arm an alert only after it drops this far below

APP_ID = "disk-space-monitor"
APP_NAME = "Disk Space Monitor"
SCRIPT_PATH = os.path.abspath(__file__)
PYTHON_BIN = sys.executable or "python3"

XDG_CONFIG = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
XDG_DATA = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
CONFIG_DIR = os.path.join(XDG_CONFIG, APP_ID)
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
AUTOSTART_PATH = os.path.join(XDG_CONFIG, "autostart", APP_ID + ".desktop")
LAUNCHER_PATH = os.path.join(XDG_DATA, "applications", APP_ID + ".desktop")

SKIP_FSTYPES = {
    "squashfs", "devtmpfs", "tmpfs", "devpts", "sysfs", "proc", "cgroup",
    "cgroup2", "overlay", "mqueue", "debugfs", "tracefs", "securityfs",
    "pstore", "autofs", "configfs", "fusectl", "ramfs", "hugetlbfs",
    "binfmt_misc", "efivarfs", "bpf", "nsfs", "none", "",
}
SKIP_PREFIXES = ("/snap", "/sys", "/proc", "/run", "/dev")


# --------------------------------------------------------------------------- #
# Colour + format helpers                                                      #
# --------------------------------------------------------------------------- #
def _hex(rgb: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % rgb


def sample_gradient(stops, t: float) -> str:
    """Sample a list of (position, (r,g,b)) stops at t in [0, 1]."""
    t = max(0.0, min(1.0, t))
    for i in range(len(stops) - 1):
        p0, c0 = stops[i]
        p1, c1 = stops[i + 1]
        if p0 <= t <= p1:
            f = 0 if p1 == p0 else (t - p0) / (p1 - p0)
            return _hex(tuple(round(c0[k] + (c1[k] - c0[k]) * f) for k in range(3)))
    return _hex(stops[-1][1])


def usage_color(pct: float) -> str:
    return sample_gradient(USAGE_STOPS, pct / 100.0)


def human_bytes(n: float) -> str:
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if abs(n) < 1024 or unit == "PB":
            return f"{n:.0f} B" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def drive_icon(mp: str, fstype: str) -> str:
    low = mp.lower()
    if mp == "/":
        return "🐧"
    if "boot" in low or "efi" in low:
        return "⚙"
    if "windows" in low or fstype in ("ntfs", "ntfs3", "fuseblk"):
        return "🪟"
    if low.startswith(("/media", "/mnt", "/run/media")):
        return "🔌"
    if fstype in ("vfat", "exfat", "msdos"):
        return "💾"
    return "💽"


def pretty_name(mp: str) -> str:
    return "Root  (/)" if mp == "/" else mp


def round_rect_points(x1, y1, x2, y2, r):
    """The control points for a smooth rounded rectangle polygon."""
    return [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]


def round_rect(cv: tk.Canvas, x1, y1, x2, y2, r, **kw):
    """Draw a smooth rounded rectangle on a Canvas; returns the item id."""
    return cv.create_polygon(round_rect_points(x1, y1, x2, y2, r),
                             smooth=True, splinesteps=24, **kw)


def load_config() -> dict:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def save_config(cfg: dict) -> None:
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=2)
    except OSError:
        pass


# --------------------------------------------------------------------------- #
# Autostart + uninstall (user-level desktop integration)                       #
# --------------------------------------------------------------------------- #
def is_autostart_enabled() -> bool:
    return os.path.exists(AUTOSTART_PATH)


def set_autostart(enabled: bool) -> bool:
    """Create or remove the ~/.config/autostart launcher. Returns success."""
    try:
        if enabled:
            os.makedirs(os.path.dirname(AUTOSTART_PATH), exist_ok=True)
            content = (
                "[Desktop Entry]\n"
                "Type=Application\n"
                f"Name={APP_NAME}\n"
                "Comment=Floating always-on-top disk usage widget\n"
                f"Exec={PYTHON_BIN} {SCRIPT_PATH}\n"
                "Icon=drive-harddisk\n"
                "Terminal=false\n"
                "X-GNOME-Autostart-enabled=true\n"
            )
            with open(AUTOSTART_PATH, "w", encoding="utf-8") as fh:
                fh.write(content)
        elif os.path.exists(AUTOSTART_PATH):
            os.remove(AUTOSTART_PATH)
        return True
    except OSError:
        return False


def perform_uninstall() -> list[str]:
    """Remove the launcher, autostart entry and saved settings.

    Deliberately leaves the program files on disk — those are version-controlled
    and the user can delete the folder by hand.
    """
    notes: list[str] = []
    for path, label in ((AUTOSTART_PATH, "autostart entry"),
                        (LAUNCHER_PATH, "app launcher")):
        try:
            if os.path.exists(path):
                os.remove(path)
                notes.append(f"✓  removed {label}")
        except OSError as exc:
            notes.append(f"✗  {label}: {exc}")
    try:
        if os.path.isdir(CONFIG_DIR):
            shutil.rmtree(CONFIG_DIR)
            notes.append("✓  removed saved settings")
    except OSError as exc:
        notes.append(f"✗  settings: {exc}")
    if not notes:
        notes.append("Nothing to remove — it was not installed.")
    return notes


@dataclass
class PartInfo:
    mountpoint: str
    device: str
    fstype: str
    total: int
    used: int
    free: int
    percent: float


def scan_partitions() -> list[PartInfo]:
    out: list[PartInfo] = []
    seen: set[str] = set()
    for part in psutil.disk_partitions(all=False):
        mp = part.mountpoint
        if part.fstype in SKIP_FSTYPES:
            continue
        if any(mp == p or mp.startswith(p + "/") for p in SKIP_PREFIXES):
            continue
        if mp in seen:
            continue
        try:
            u = psutil.disk_usage(mp)
        except (PermissionError, OSError):
            continue
        seen.add(mp)
        out.append(PartInfo(mp, part.device, part.fstype,
                            u.total, u.used, u.free, u.percent))
    out.sort(key=lambda p: (p.mountpoint != "/", p.mountpoint))
    return out


def open_in_files(mountpoint: str) -> None:
    try:
        subprocess.Popen(["xdg-open", mountpoint],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def scan_largest(mountpoint: str, limit: int = 20) -> list[tuple[int, str]]:
    """Largest immediate children of a mount via `du`. Blocking — call off the
    main thread. `-x` stays on one filesystem; permission errors are ignored."""
    try:
        proc = subprocess.run(
            ["du", "-x", "--max-depth=1", "-b", mountpoint],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return []
    items: list[tuple[int, str]] = []
    for line in proc.stdout.splitlines():
        cols = line.split("\t", 1)
        if len(cols) != 2:
            continue
        try:
            size = int(cols[0])
        except ValueError:
            continue
        if cols[1] == mountpoint:      # skip the mount's own grand total
            continue
        items.append((size, cols[1]))
    items.sort(key=lambda t: t[0], reverse=True)
    return items[:limit]


# --------------------------------------------------------------------------- #
# A single partition card (fully Canvas-drawn for a polished look)             #
# --------------------------------------------------------------------------- #
class PartitionCard:
    def __init__(self, parent, app: "DiskMonitorApp", info: PartInfo):
        self.app = app
        self.mountpoint = info.mountpoint
        self.prev_used = info.used
        self.target = info.percent
        self.display = info.percent  # animated value

        self.compact = app.compact
        self.h = CARD_H_COMPACT if self.compact else CARD_H
        self.w = app.width - 2 * PAD

        self.cv = tk.Canvas(parent, width=self.w, height=self.h,
                            bg=BG, highlightthickness=0, bd=0)
        # NB: placement is handled centrally by DiskMonitorApp._relayout_all()
        # (grid), so the card no longer packs itself.

        self.bar_x1 = 16
        self.bar_x2 = self.w - 16
        top_y = 20
        bar_y = self.h - 14 if self.compact else 46

        self.card_bg = round_rect(self.cv, 1, 1, self.w - 1, self.h - 1,
                                  RADIUS, fill=CARD, outline=BORDER, width=1)

        self.icon_item = self.cv.create_text(
            16, top_y, text=drive_icon(info.mountpoint, info.fstype),
            anchor="w", font=app.font_icon, fill=FG)
        self.name_item = self.cv.create_text(
            40, top_y, text=pretty_name(info.mountpoint),
            anchor="w", font=app.font_name, fill=FG)
        self.pct_item = self.cv.create_text(
            self.w - 16, top_y, text="", anchor="e",
            font=app.font_pct, fill=FG)

        self.track = self.cv.create_line(
            self.bar_x1, bar_y, self.bar_x2, bar_y,
            width=BAR_THICK, fill=TRACK, capstyle="round")
        self.fill = self.cv.create_line(
            self.bar_x1, bar_y, self.bar_x1, bar_y,
            width=BAR_THICK, fill=usage_color(self.display), capstyle="round")
        self.bar_y = bar_y

        self.io_item = self.cv.create_text(
            16, 64, text="", anchor="w", font=app.font_small, fill=MUTED)
        self.detail_item = self.cv.create_text(
            16, self.h - 13, text="", anchor="w",
            font=app.font_small, fill=MUTED)
        self.delta_item = self.cv.create_text(
            self.w - 16, self.h - 13, text="", anchor="e",
            font=app.font_small, fill=MUTED)
        if self.compact:
            self.cv.itemconfig(self.detail_item, state="hidden")
            self.cv.itemconfig(self.delta_item, state="hidden")
            self.cv.itemconfig(self.io_item, state="hidden")

        # Interactions
        app.make_draggable(self.cv)
        self.cv.bind("<Double-Button-1>",
                     lambda _e, m=info.mountpoint: open_in_files(m))
        self.cv.bind("<Button-3>",
                     lambda e, m=info.mountpoint: app.show_card_menu(e, m))
        self.cv.bind("<Enter>", lambda _e: self.cv.itemconfig(self.card_bg, fill=CARD_HOVER))
        self.cv.bind("<Leave>", lambda _e: self.cv.itemconfig(self.card_bg, fill=CARD))

        self.set_data(info)
        self._redraw_bar()

    def set_data(self, info: PartInfo, io: tuple[float, float] | None = None) -> None:
        self.target = info.percent
        if not self.compact:
            self.cv.itemconfig(
                self.detail_item,
                text=f"{human_bytes(info.used)} / {human_bytes(info.total)}"
                     f"   ·   {human_bytes(info.free)} free")
            delta = info.used - self.prev_used
            if abs(delta) >= 512 * 1024:
                if delta > 0:
                    self.cv.itemconfig(self.delta_item,
                                       text=f"▲ {human_bytes(delta)}", fill="#ffb86c")
                else:
                    self.cv.itemconfig(self.delta_item,
                                       text=f"▼ {human_bytes(-delta)}", fill="#50fa7b")
            else:
                self.cv.itemconfig(self.delta_item, text="")
            if self.app.show_io and io is not None:
                r, w = io
                self.cv.itemconfig(
                    self.io_item,
                    text=f"↓ {human_bytes(r)}/s    ↑ {human_bytes(w)}/s")
            else:
                self.cv.itemconfig(self.io_item, text="")
        self.prev_used = info.used

    def relayout(self, w: int) -> None:
        """Reflow the card to a new width (used by live resize)."""
        self.w = w
        self.cv.config(width=w)
        self.cv.coords(self.card_bg, *round_rect_points(1, 1, w - 1, self.h - 1, RADIUS))
        self.bar_x2 = w - 16
        self.cv.coords(self.track, self.bar_x1, self.bar_y, self.bar_x2, self.bar_y)
        self.cv.coords(self.pct_item, w - 16, 20)
        self.cv.coords(self.delta_item, w - 16, self.h - 13)
        self._redraw_bar()

    def step(self) -> None:
        """Ease the animated value toward the target; redraw bar + percent."""
        diff = self.target - self.display
        if abs(diff) < 0.1:
            self.display = self.target
        else:
            self.display += diff * 0.22
        self._redraw_bar()

    def _redraw_bar(self) -> None:
        color = usage_color(self.display)
        span = self.bar_x2 - self.bar_x1
        fill_w = span * max(0.0, min(self.display, 100)) / 100.0
        if fill_w < 0.5:
            self.cv.itemconfig(self.fill, state="hidden")
        else:
            self.cv.itemconfig(self.fill, state="normal", fill=color)
            self.cv.coords(self.fill, self.bar_x1, self.bar_y,
                           self.bar_x1 + fill_w, self.bar_y)
        self.cv.itemconfig(self.pct_item, text=f"{round(self.display)}%", fill=color)

    def destroy(self) -> None:
        self.cv.destroy()


# --------------------------------------------------------------------------- #
# Main application window                                                       #
# --------------------------------------------------------------------------- #
class DiskMonitorApp:
    def __init__(self) -> None:
        self.cfg = load_config()
        self.interval = int(self.cfg.get("interval_ms", DEFAULT_INTERVAL_MS))
        self.pinned = bool(self.cfg.get("pinned", True))
        self.compact = bool(self.cfg.get("compact", False))
        self.width = self._clamp_width(self.cfg.get("width", DEFAULT_WIDTH))
        self.alpha = max(0.2, min(1.0, float(self.cfg.get("alpha", ALPHA))))
        self.theme = apply_palette(self.cfg.get("theme", "dark"))
        self.alerts_enabled = bool(self.cfg.get("alerts_enabled", True))
        self.alert_threshold = int(self.cfg.get("alert_threshold", DEFAULT_ALERT_PCT))
        self.show_io = bool(self.cfg.get("show_io", True))

        self.settings_win: tk.Toplevel | None = None
        self._suspend_width = False
        self._resize_anchor = {"x": 0, "w": self.width}

        # window-state + feature state
        self.maximized = False
        self._minimized = False
        self.paused = False
        self.cols = 1
        self._normal: tuple[int, int, int] | None = None   # (width, x, y) pre-maximize
        self._alerted: set[str] = set()
        self._io_prev: dict[str, tuple[int, int]] = {}
        self._io_time: float | None = None

        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", self.pinned)
        try:
            self.root.attributes("-alpha", 0.0)   # start invisible for fade-in
        except tk.TclError:
            pass

        self.font_name = tkfont.Font(family="DejaVu Sans", size=10, weight="bold")
        self.font_pct = tkfont.Font(family="DejaVu Sans", size=12, weight="bold")
        self.font_small = tkfont.Font(family="DejaVu Sans", size=8)
        self.font_title = tkfont.Font(family="DejaVu Sans", size=11, weight="bold")
        self.font_icon = tkfont.Font(family="DejaVu Sans", size=12)

        self._drag = {"x": 0, "y": 0}
        self.cards: dict[str, PartitionCard] = {}
        self._last_keys: tuple[str, ...] = ()

        self._build_ui()
        self._restore_position()
        self.root.bind("<Map>", self._on_map)
        self._tick()
        self._animate()
        self._fade_in(0)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)

    def _build_ui(self) -> None:
        """Build the whole surface (outer frame, header, menu, body, grip).

        Split out of __init__ so a theme switch can tear the chrome down and
        rebuild it against the new palette (colours are baked in at creation).
        """
        self.root.configure(bg=BORDER)             # acts as 1px outer hairline
        self.outer = tk.Frame(self.root, bg=BG)
        self.outer.pack(fill="both", expand=True, padx=1, pady=1)
        self._build_header()
        self._build_menu()
        self.body = tk.Frame(self.outer, bg=BG)
        self.body.pack(fill="both", expand=True, padx=PAD, pady=(PAD, PAD - CARD_GAP))
        self._build_grip()

    @staticmethod
    def _clamp_width(value) -> int:
        try:
            return max(MIN_WIDTH, min(MAX_WIDTH, int(value)))
        except (TypeError, ValueError):
            return DEFAULT_WIDTH

    # ---- chrome ---------------------------------------------------------- #
    def _build_header(self) -> None:
        hdr = tk.Frame(self.outer, bg=HEADER_BG, height=HEADER_H)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        title = tk.Label(hdr, text=self._title_text(), bg=HEADER_BG, fg=FG,
                         font=self.font_title)
        title.pack(side="left", padx=(6, 0))
        self.title_label = title

        # Packed side="right", so creation order is right→left. This yields the
        # normal-window grouping at the far right: — ▢ ✕ (minimize, maximize, close).
        self.btn_close = self._chrome_btn(hdr, "✕", self.quit, DANGER)
        self.btn_max = self._chrome_btn(
            hdr, "❐" if self.maximized else "▢", self.toggle_maximize, MUTED)
        self.btn_min = self._chrome_btn(hdr, "—", self.minimize, MUTED)
        self.btn_compact = self._chrome_btn(hdr, "▭", self.toggle_compact, MUTED)
        self.btn_pin = self._chrome_btn(
            hdr, "📌", self.toggle_pin, ACCENT if self.pinned else MUTED)
        self.btn_settings = self._chrome_btn(hdr, "⚙", self.open_settings, MUTED)

        for w in (hdr, title):
            self.make_draggable(w)
            w.bind("<Button-3>", self.show_menu)

        # gradient accent line under the header
        accent = tk.Canvas(self.outer, height=3, bg=HEADER_BG,
                           highlightthickness=0, bd=0)
        accent.pack(fill="x")
        self._accent = accent
        accent.bind("<Configure>", self._draw_accent)

    def _draw_accent(self, event) -> None:
        cv = self._accent
        cv.delete("grad")
        w = max(event.width, 1)
        for x in range(w):
            cv.create_line(x, 0, x, 3, tags="grad",
                           fill=sample_gradient(HEADER_STOPS, x / w))

    def _chrome_btn(self, parent, text, cmd, color):
        b = tk.Label(parent, text=text, bg=HEADER_BG, fg=color,
                     font=self.font_title, cursor="hand2", width=2)
        b.pack(side="right", padx=2)
        b.bind("<Button-1>", lambda _e: cmd())
        b.bind("<Enter>", lambda _e, x=b: x.config(bg=CARD_HOVER, fg=FG))
        b.bind("<Leave>", lambda _e, x=b, c=color: x.config(bg=HEADER_BG, fg=c))
        return b

    def _build_grip(self) -> None:
        """A small drag handle in the bottom-right corner to resize the width."""
        grip = tk.Canvas(self.outer, width=16, height=16, bg=BG,
                         highlightthickness=0, bd=0, cursor="bottom_right_corner")
        for off in (3, 8, 13):
            grip.create_line(16 - off, 16, 16, 16 - off, fill=MUTED)
        grip.place(relx=1.0, rely=1.0, x=-2, y=-2, anchor="se")
        grip.bind("<Button-1>", self._start_resize)
        grip.bind("<B1-Motion>", self._on_resize)
        self._grip = grip

    def _build_menu(self) -> None:
        self.menu = tk.Menu(self.root, tearoff=0, bg=CARD, fg=FG,
                            activebackground=ACCENT, activeforeground=BG, bd=0)
        self.menu.add_command(label="Settings…", command=self.open_settings)
        self.menu.add_command(label="Refresh now", command=self.refresh)
        speed = tk.Menu(self.menu, tearoff=0, bg=CARD, fg=FG,
                        activebackground=ACCENT, activeforeground=BG)
        for label, ms in (("Fast (0.5s)", 500), ("Normal (1.5s)", 1500),
                          ("Relaxed (3s)", 3000), ("Slow (5s)", 5000)):
            speed.add_command(label=label, command=lambda m=ms: self.set_interval(m))
        self.menu.add_cascade(label="Update speed", menu=speed)
        self.menu.add_separator()
        self.menu.add_command(label="Copy usage report", command=self.copy_report)
        self.menu.add_command(label="Pause / resume updates", command=self.toggle_pause)
        self.menu.add_command(label="Switch light / dark theme", command=self.toggle_theme)
        self.menu.add_separator()
        self.menu.add_command(label="Toggle compact view", command=self.toggle_compact)
        self.menu.add_command(label="Toggle always-on-top", command=self.toggle_pin)
        self.menu.add_separator()
        self.menu.add_command(label="Quit", command=self.quit)

    def show_menu(self, event) -> None:
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    # ---- dragging -------------------------------------------------------- #
    def make_draggable(self, widget: tk.Widget) -> None:
        widget.bind("<Button-1>", self._start_drag, add="+")
        widget.bind("<B1-Motion>", self._on_drag, add="+")

    def _start_drag(self, event) -> None:
        self._drag["x"] = event.x_root - self.root.winfo_x()
        self._drag["y"] = event.y_root - self.root.winfo_y()

    def _on_drag(self, event) -> None:
        x = event.x_root - self._drag["x"]
        y = event.y_root - self._drag["y"]
        self.root.geometry(f"+{x}+{y}")

    # ---- resizing -------------------------------------------------------- #
    def _start_resize(self, event) -> None:
        self._resize_anchor = {"x": event.x_root, "w": self.width}

    def _on_resize(self, event) -> None:
        dx = event.x_root - self._resize_anchor["x"]
        self.apply_width(self._resize_anchor["w"] + dx, from_grip=True)

    def apply_width(self, width, from_grip: bool = False) -> None:
        width = self._clamp_width(width)
        self.width = width
        if self.maximized:
            return   # geometry is pinned to the work area while maximized
        self._relayout_all()
        if from_grip and getattr(self, "width_scale", None) is not None \
                and self.settings_win is not None and self.settings_win.winfo_exists():
            self._suspend_width = True
            try:
                self.width_scale.set(width)
            finally:
                self._suspend_width = False

    # ---- toggles --------------------------------------------------------- #
    def set_pinned(self, value) -> None:
        self.pinned = bool(value)
        self.root.attributes("-topmost", self.pinned)
        self.btn_pin.config(fg=ACCENT if self.pinned else MUTED)
        if getattr(self, "var_pin", None) is not None:
            self.var_pin.set(self.pinned)

    def toggle_pin(self) -> None:
        self.set_pinned(not self.pinned)

    def set_compact(self, value) -> None:
        value = bool(value)
        if value == self.compact:
            return
        self.compact = value
        self._last_keys = ()   # force rebuild at new height
        self.refresh()
        if getattr(self, "var_compact", None) is not None:
            self.var_compact.set(self.compact)

    def toggle_compact(self) -> None:
        self.set_compact(not self.compact)

    def set_interval(self, ms: int) -> None:
        self.interval = ms

    def set_alerts_enabled(self, value) -> None:
        self.alerts_enabled = bool(value)
        if not self.alerts_enabled:
            self._alerted.clear()

    def set_alert_threshold(self, value) -> None:
        self.alert_threshold = max(50, min(99, int(round(float(value)))))
        self._alerted.clear()   # re-evaluate against the new threshold next tick

    def set_show_io(self, value) -> None:
        self.show_io = bool(value)

    def set_alpha(self, value: float) -> None:
        self.alpha = max(0.2, min(1.0, float(value)))
        try:
            self.root.attributes("-alpha", self.alpha)
        except tk.TclError:
            pass

    def reset_position(self) -> None:
        if self.maximized:
            self.restore()
        self.root.geometry("+60+60")

    def _title_text(self) -> str:
        return "  ⏸  Disk Monitor" if getattr(self, "paused", False) \
            else "  💽  Disk Monitor"

    # ---- window state: minimize / maximize ------------------------------- #
    def minimize(self) -> None:
        """Minimize to the taskbar. A borderless (overrideredirect) window has
        no taskbar button and iconify() is a no-op on it, so hand the window
        back to the WM first; _on_map re-applies the custom chrome on restore."""
        self._saved_geom = self.root.geometry()
        self._minimized = True
        try:
            self.root.overrideredirect(False)
            self.root.update_idletasks()
            self.root.iconify()
        except tk.TclError:
            self._minimized = False

    def _on_map(self, event=None) -> None:
        if event is not None and event.widget is not self.root:
            return
        if not self._minimized:
            return
        self._minimized = False

        def _restore_chrome() -> None:
            try:
                self.root.overrideredirect(True)
                if getattr(self, "_saved_geom", None):
                    self.root.geometry(self._saved_geom)
                self.root.attributes("-topmost", self.pinned)
                self.root.attributes("-alpha", self.alpha)
            except tk.TclError:
                pass

        self.root.after(10, _restore_chrome)

    def _work_area(self) -> tuple[int, int, int, int]:
        """Global work area (x, y, w, h) excluding panels, via _NET_WORKAREA.
        On multi-monitor setups this is the union of all monitors — see
        _current_area() for a per-monitor rectangle. Falls back to full screen."""
        try:
            out = subprocess.check_output(
                ["xprop", "-root", "_NET_WORKAREA"],
                stderr=subprocess.DEVNULL, text=True)
            nums = [int(n) for n in re.findall(r"\d+", out.split("=", 1)[1])]
            if len(nums) >= 4:
                return nums[0], nums[1], nums[2], nums[3]
        except (OSError, ValueError, IndexError):
            pass
        return 0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight()

    def _monitors(self) -> list[tuple[int, int, int, int]]:
        """Connected monitors as (x, y, w, h), via xrandr --listmonitors."""
        mons: list[tuple[int, int, int, int]] = []
        try:
            out = subprocess.check_output(
                ["xrandr", "--listmonitors"], stderr=subprocess.DEVNULL, text=True)
        except OSError:
            return mons
        for line in out.splitlines()[1:]:               # skip the count header
            m = re.search(r"(\d+)/\d+x(\d+)/\d+\+(\d+)\+(\d+)", line)
            if m:
                w, h, x, y = (int(g) for g in m.groups())
                mons.append((x, y, w, h))
        return mons

    def _current_area(self) -> tuple[int, int, int, int]:
        """Work area of the monitor the window sits on (multi-monitor aware).
        Uses the monitor rectangle for x/width and clips the vertical band to
        the global work area so a top/bottom panel is respected. Falls back to
        the global work area (single-monitor case)."""
        wx, wy, ww, wh = self._work_area()
        mons = self._monitors()
        if len(mons) > 1:
            cx = self.root.winfo_x() + self.root.winfo_width() // 2
            cy = self.root.winfo_y() + self.root.winfo_height() // 2
            for (mx, my, mw, mh) in mons:
                if mx <= cx < mx + mw and my <= cy < my + mh:
                    top = max(my, wy)
                    bot = min(my + mh, wy + wh)
                    if bot - top < mh // 2:             # struts don't apply here
                        top, bot = my, my + mh
                    return mx, top, mw, bot - top
        return wx, wy, ww, wh

    def toggle_maximize(self) -> None:
        self.restore() if self.maximized else self.maximize()

    def maximize(self) -> None:
        if self.maximized:
            return
        self._normal = (self.width, self.root.winfo_x(), self.root.winfo_y())
        x, y, w, h = self._current_area()
        self.maximized = True
        self.width = w
        self.btn_max.config(text="❐")
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self._relayout_all()

    def restore(self) -> None:
        if not self.maximized:
            return
        self.maximized = False
        self.btn_max.config(text="▢")
        if self._normal:
            width, nx, ny = self._normal
            self.width = self._clamp_width(width)
        else:
            nx, ny = 60, 60
        self._relayout_all()               # not maximized now → _resize sets height
        self.root.geometry(f"+{nx}+{ny}")

    # ---- card layout (grid: 1 column, or N columns when maximized) ------- #
    def _relayout_all(self) -> None:
        cards = list(self.cards.values())
        avail = max(MIN_WIDTH, self.width) - 2 - 2 * PAD
        cols = 1
        if self.maximized:
            cols = max(1, (avail + CARD_GAP) // (MIN_CARD + CARD_GAP))
        self.cols = cols
        cell = (avail - (cols - 1) * CARD_GAP) // cols
        for c in range(cols):
            self.body.grid_columnconfigure(c, weight=1, uniform="cards")
        for c in range(cols, 64):
            self.body.grid_columnconfigure(c, weight=0, uniform="")
        for i, card in enumerate(cards):
            card.relayout(cell)
            card.cv.grid(
                row=i // cols, column=i % cols,
                padx=(0 if i % cols == 0 else CARD_GAP, 0),
                pady=(0, CARD_GAP), sticky="n")
        rows = (len(cards) + cols - 1) // cols if cols else 0
        self._resize(rows)

    # ---- theme ----------------------------------------------------------- #
    def apply_theme(self, name: str) -> None:
        name = name if name in THEMES else "dark"
        if name == self.theme:
            return
        self.theme = apply_palette(name)
        self.cfg["theme"] = name
        self._rebuild_ui()
        if getattr(self, "var_theme", None) is not None:
            self.var_theme.set(self.theme == "light")

    def toggle_theme(self) -> None:
        self.apply_theme("light" if self.theme == "dark" else "dark")

    def _rebuild_ui(self) -> None:
        """Tear down and rebuild the chrome against the active palette (colours
        are baked in at widget-creation time). Root + geometry are preserved."""
        for c in self.cards.values():
            c.destroy()
        self.cards.clear()
        self._last_keys = ()
        if getattr(self, "menu", None) is not None:
            self.menu.destroy()
        self.outer.destroy()
        self._build_ui()
        self.refresh()

    # ---- extras: copy report / pause ------------------------------------ #
    def copy_report(self) -> None:
        parts = scan_partitions()
        lines = [f"{APP_NAME} — {len(parts)} partition(s)", ""]
        for p in parts:
            lines.append(
                f"{pretty_name(p.mountpoint)}: {p.percent:.0f}%  "
                f"{human_bytes(p.used)} / {human_bytes(p.total)}  "
                f"({human_bytes(p.free)} free)  [{p.fstype}]")
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append("\n".join(lines))
        except tk.TclError:
            pass

    def toggle_pause(self) -> None:
        self.paused = not self.paused
        if getattr(self, "title_label", None) is not None:
            self.title_label.config(text=self._title_text())
        if getattr(self, "var_pause", None) is not None:
            self.var_pause.set(self.paused)

    # ---- alerts ---------------------------------------------------------- #
    def _check_alerts(self, parts) -> None:
        if not self.alerts_enabled:
            self._alerted.clear()
            return
        thr = self.alert_threshold
        for p in parts:
            if p.percent >= thr and p.mountpoint not in self._alerted:
                self._alerted.add(p.mountpoint)
                self.notify_alert(p)
            elif p.percent < thr - ALERT_HYSTERESIS and p.mountpoint in self._alerted:
                self._alerted.discard(p.mountpoint)

    def notify_alert(self, part: PartInfo) -> None:
        if not shutil.which("notify-send"):
            return
        title = f"Disk almost full: {pretty_name(part.mountpoint)}"
        body = (f"{part.percent:.0f}% used — {human_bytes(part.free)} free "
                f"of {human_bytes(part.total)}")
        try:
            subprocess.Popen(
                ["notify-send", "-u", "critical", "-a", APP_NAME, title, body],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            pass

    # ---- disk I/O -------------------------------------------------------- #
    def _compute_io(self, parts) -> dict[str, tuple[float, float]]:
        """Per-mount (read, write) bytes/sec since the previous refresh."""
        rates: dict[str, tuple[float, float]] = {}
        if not self.show_io:
            self._io_prev = {}
            self._io_time = None
            return rates
        try:
            counters = psutil.disk_io_counters(perdisk=True)
        except Exception:
            return rates
        now = time.monotonic()
        dt = (now - self._io_time) if self._io_time else 0.0
        self._io_time = now
        cur: dict[str, tuple[int, int]] = {}
        for p in parts:
            key = os.path.basename(p.device)      # /dev/sda1 -> sda1
            c = counters.get(key)
            if c is None:
                continue
            cur[p.mountpoint] = (c.read_bytes, c.write_bytes)
            prev = self._io_prev.get(p.mountpoint)
            if prev and dt > 0:
                r = max(0, c.read_bytes - prev[0]) / dt
                w = max(0, c.write_bytes - prev[1]) / dt
                rates[p.mountpoint] = (r, w)
        self._io_prev = cur
        return rates

    # ---- largest items --------------------------------------------------- #
    def show_card_menu(self, event, mountpoint: str) -> None:
        m = tk.Menu(self.root, tearoff=0, bg=CARD, fg=FG,
                    activebackground=ACCENT, activeforeground=BG, bd=0)
        m.add_command(label=f"Open  {pretty_name(mountpoint)}",
                      command=lambda: open_in_files(mountpoint))
        m.add_command(label="Find largest items here…",
                      command=lambda: self.open_largest(mountpoint))
        m.add_separator()
        m.add_command(label="Copy usage report", command=self.copy_report)
        m.add_command(label="Settings…", command=self.open_settings)
        m.add_command(label="Refresh now", command=self.refresh)
        m.add_separator()
        m.add_command(label="Quit", command=self.quit)
        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()
            self.root.after(200, m.destroy)

    def open_largest(self, mountpoint: str) -> None:
        win = tk.Toplevel(self.root)
        win.title(f"Largest items · {mountpoint}")
        win.configure(bg=BG)
        win.attributes("-topmost", True)
        win.geometry(
            f"480x520+{self.root.winfo_x() + 40}+{self.root.winfo_y() + 40}")

        head = tk.Frame(win, bg=HEADER_BG)
        head.pack(fill="x")
        tk.Label(head, text=f"  📁  Largest items in {mountpoint}", bg=HEADER_BG,
                 fg=FG, font=self.font_title).pack(side="left", padx=10, pady=9)

        status = tk.Label(win, text="Scanning…  (this can take a while on big disks)",
                          bg=BG, fg=MUTED, font=self.font_small, anchor="w")
        status.pack(fill="x", padx=14, pady=(10, 6))

        rows = tk.Frame(win, bg=BG)
        rows.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        alive = {"open": True}
        win.protocol("WM_DELETE_WINDOW",
                     lambda: (alive.update(open=False), win.destroy()))

        def worker() -> None:
            results = scan_largest(mountpoint)

            def show() -> None:
                if not alive["open"] or not win.winfo_exists():
                    return
                if not results:
                    status.config(text="Nothing found (or permission denied).")
                    return
                status.config(
                    text=f"Top {len(results)} items — click a row to open its location")
                for size, path in results:
                    row = tk.Label(
                        rows, text=f"{human_bytes(size):>10}    {path}",
                        bg=CARD, fg=FG, font=self.font_small, anchor="w",
                        cursor="hand2", padx=8, pady=4)
                    row.pack(fill="x", pady=1)
                    row.bind("<Button-1>",
                             lambda _e, p=path: open_in_files(os.path.dirname(p) or p))
                    row.bind("<Enter>", lambda _e, r=row: r.config(bg=CARD_HOVER))
                    row.bind("<Leave>", lambda _e, r=row: r.config(bg=CARD))

            self.root.after(0, show)

        threading.Thread(target=worker, daemon=True).start()

    # ---- settings window ------------------------------------------------- #
    def open_settings(self) -> None:
        if self.settings_win is not None and self.settings_win.winfo_exists():
            self.settings_win.deiconify()
            self.settings_win.lift()
            self.settings_win.focus_force()
            return

        win = tk.Toplevel(self.root)
        self.settings_win = win
        win.title(f"{APP_NAME} · Settings")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.attributes("-topmost", True)
        win.geometry(f"+{self.root.winfo_x() + 24}+{self.root.winfo_y() + 24}")
        win.protocol("WM_DELETE_WINDOW", self._close_settings)

        head = tk.Frame(win, bg=HEADER_BG)
        head.pack(fill="x")
        tk.Label(head, text="  ⚙  Settings", bg=HEADER_BG, fg=FG,
                 font=self.font_title).pack(side="left", padx=10, pady=9)

        body = tk.Frame(win, bg=BG)
        body.pack(fill="both", expand=True)

        def heading(text):
            tk.Label(body, text=text.upper(), bg=BG, fg=MUTED, font=self.font_small,
                     anchor="w").pack(fill="x", padx=16, pady=(14, 4))

        def toggle(text, value, cmd):
            var = tk.BooleanVar(value=value)
            tk.Checkbutton(
                body, text="  " + text, variable=var, command=lambda: cmd(var),
                bg=BG, fg=FG, selectcolor=CARD, activebackground=BG,
                activeforeground=FG, font=self.font_name, anchor="w",
                highlightthickness=0, bd=0, padx=8).pack(fill="x", padx=14, pady=1)
            return var

        def slider(text, frm, to, res, value, cmd):
            row = tk.Frame(body, bg=BG)
            row.pack(fill="x", padx=16, pady=(2, 2))
            tk.Label(row, text=text, bg=BG, fg=FG, font=self.font_name,
                     anchor="w").pack(fill="x")
            scl = tk.Scale(row, from_=frm, to=to, resolution=res, orient="horizontal",
                           bg=BG, fg=MUTED, troughcolor=TRACK, highlightthickness=0,
                           bd=0, sliderrelief="flat", activebackground=ACCENT,
                           font=self.font_small, length=280)
            scl.set(value)
            scl.config(command=cmd)
            scl.pack(fill="x")
            return scl

        def action(text, cmd, fg=FG):
            b = tk.Label(body, text=text, bg=CARD, fg=fg, font=self.font_name,
                         cursor="hand2", pady=9)
            b.pack(fill="x", padx=14, pady=4)
            b.bind("<Button-1>", lambda _e: cmd())
            b.bind("<Enter>", lambda _e: b.config(bg=CARD_HOVER))
            b.bind("<Leave>", lambda _e: b.config(bg=CARD))
            return b

        heading("Behaviour")
        self.var_autostart = toggle("Start on login", is_autostart_enabled(),
                                    self._on_autostart_toggle)
        self.var_pin = toggle("Always on top", self.pinned,
                              lambda v: self.set_pinned(v.get()))
        self.var_compact = toggle("Compact view", self.compact,
                                  lambda v: self.set_compact(v.get()))
        self.var_pause = toggle("Pause updates", self.paused,
                                lambda v: (self.toggle_pause()
                                           if v.get() != self.paused else None))
        self.var_io = toggle("Show disk I/O speeds", self.show_io,
                             lambda v: self.set_show_io(v.get()))

        heading("Alerts")
        self.var_alerts = toggle("Disk-full desktop alerts", self.alerts_enabled,
                                 lambda v: self.set_alerts_enabled(v.get()))
        slider("Alert threshold (%)", 50, 99, 1, self.alert_threshold,
               lambda val: self.set_alert_threshold(val))

        heading("Update speed")
        slider("Refresh interval (seconds)", 0.3, 5.0, 0.1, self.interval / 1000.0,
               lambda val: self.set_interval(int(round(float(val) * 1000))))

        heading("Appearance")
        self.var_theme = toggle("Light theme", self.theme == "light",
                                lambda v: self.apply_theme("light" if v.get() else "dark"))
        slider("Opacity", 0.3, 1.0, 0.05, self.alpha,
               lambda val: self.set_alpha(val))
        self.width_scale = slider("Width", MIN_WIDTH, MAX_WIDTH, 2, self.width,
                                  self._on_width_slider)

        heading("Window")
        action("Maximize / restore", self.toggle_maximize)
        action("Reset position", self.reset_position)
        action("Open settings folder", lambda: open_in_files(CONFIG_DIR))

        heading("Danger zone")
        action("Uninstall Disk Monitor…", self.uninstall, fg=DANGER)

        tk.Label(body, text=f"{APP_NAME}  ·  v{__version__}", bg=BG, fg=MUTED,
                 font=self.font_small).pack(pady=(14, 10))

    def _close_settings(self) -> None:
        if self.settings_win is not None:
            self.settings_win.destroy()
            self.settings_win = None

    def _on_autostart_toggle(self, var: tk.BooleanVar) -> None:
        if not set_autostart(var.get()):
            var.set(is_autostart_enabled())
            messagebox.showwarning(
                APP_NAME, "Could not update the autostart entry.",
                parent=self.settings_win or self.root)

    def _on_width_slider(self, val) -> None:
        if self._suspend_width:
            return
        self.apply_width(val)

    def uninstall(self) -> None:
        parent = self.settings_win or self.root
        msg = (
            "This removes the app launcher, the autostart entry and your "
            "saved settings.\n\n"
            "The program files in\n"
            f"    {os.path.dirname(SCRIPT_PATH)}\n"
            "are NOT deleted — remove that folder by hand if you want.\n\n"
            "Uninstall now? The widget will close afterwards."
        )
        if not messagebox.askyesno(f"Uninstall {APP_NAME}", msg, parent=parent):
            return
        notes = perform_uninstall()
        messagebox.showinfo(
            "Uninstalled",
            f"{APP_NAME} has been uninstalled.\n\n" + "\n".join(notes)
            + f"\n\nProgram folder kept at:\n    {os.path.dirname(SCRIPT_PATH)}",
            parent=parent)
        # Skip quit()'s config save — we just deleted the config on purpose.
        self.root.destroy()

    # ---- geometry / fx --------------------------------------------------- #
    def _restore_position(self) -> None:
        x, y = self.cfg.get("x"), self.cfg.get("y")
        self.root.geometry(f"+{int(x)}+{int(y)}" if x is not None else "+60+60")

    def _resize(self, n_rows: int) -> None:
        if self.maximized:
            return   # size is pinned to the work area while maximized
        card_h = CARD_H_COMPACT if self.compact else CARD_H
        body_h = (PAD + n_rows * (card_h + CARD_GAP) + (PAD - CARD_GAP)) if n_rows \
            else PAD * 2
        height = 1 + HEADER_H + 3 + body_h + 1
        self.root.geometry(f"{self.width}x{height}")

    def _fade_in(self, step: int) -> None:
        target = self.alpha
        val = min(target, step * (target / 12))
        try:
            self.root.attributes("-alpha", val)
        except tk.TclError:
            return
        if val < target:
            self.root.after(16, lambda: self._fade_in(step + 1))

    # ---- loops ----------------------------------------------------------- #
    def _tick(self) -> None:
        """The periodic loop. Kept separate from refresh() so one-shot callers
        (compact toggle, theme rebuild, 'Refresh now') don't spawn extra loops."""
        if not self.paused:
            self.refresh()
        self.root.after(self.interval, self._tick)

    def refresh(self) -> None:
        parts = scan_partitions()
        io = self._compute_io(parts)
        keys = tuple(p.mountpoint for p in parts)
        if keys != self._last_keys:
            for c in self.cards.values():
                c.destroy()
            self.cards.clear()
            for info in parts:
                self.cards[info.mountpoint] = PartitionCard(self.body, self, info)
            self._last_keys = keys
            self._relayout_all()

        for info in parts:
            self.cards[info.mountpoint].set_data(info, io.get(info.mountpoint))

        self._check_alerts(parts)

        if self.pinned:
            self.root.attributes("-topmost", True)

    def _animate(self) -> None:
        for c in self.cards.values():
            c.step()
        self.root.after(ANIM_MS, self._animate)

    # ---- shutdown -------------------------------------------------------- #
    def quit(self) -> None:
        # Persist the *normal* geometry, not the maximized one.
        if self.maximized and self._normal:
            width, x, y = self._normal
        else:
            width = self.width
            x, y = self.root.winfo_x(), self.root.winfo_y()
        self.cfg.update({
            "x": x, "y": y,
            "interval_ms": self.interval, "pinned": self.pinned,
            "compact": self.compact, "width": width,
            "alpha": round(self.alpha, 3),
            "theme": self.theme,
            "alerts_enabled": self.alerts_enabled,
            "alert_threshold": self.alert_threshold,
            "show_io": self.show_io,
        })
        save_config(self.cfg)
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    DiskMonitorApp().run()


if __name__ == "__main__":
    main()
