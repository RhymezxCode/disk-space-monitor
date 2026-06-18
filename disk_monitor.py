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

import json
import os
import subprocess
import tkinter as tk
import tkinter.font as tkfont
from dataclasses import dataclass

import psutil

# --------------------------------------------------------------------------- #
# Theme                                                                        #
# --------------------------------------------------------------------------- #
BG = "#16171f"          # window background
CARD = "#23252f"        # partition card
CARD_HOVER = "#2a2d39"  # card on hover
HEADER_BG = "#1b1c24"
BORDER = "#333645"      # hairline outline
FG = "#f4f5fb"
MUTED = "#8b90a6"
TRACK = "#3a3d4d"       # progress bar groove
ACCENT = "#bd93f9"

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

ALPHA = 0.96            # final window opacity (0..1)
WIDTH = 348             # widget width in px
PAD = 12                # window inner padding
CARD_GAP = 9            # gap between cards
CARD_H = 78             # normal card height
CARD_H_COMPACT = 50     # compact card height
HEADER_H = 42
BAR_THICK = 10          # progress bar thickness
RADIUS = 16             # card corner radius

DEFAULT_INTERVAL_MS = 1500   # data refresh cadence
ANIM_MS = 33                 # ~30 fps animation tick

CONFIG_DIR = os.path.join(
    os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
    "disk-space-monitor",
)
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

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


def round_rect(cv: tk.Canvas, x1, y1, x2, y2, r, **kw):
    """Draw a smooth rounded rectangle on a Canvas; returns the item id."""
    pts = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return cv.create_polygon(pts, smooth=True, splinesteps=24, **kw)


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
        self.w = WIDTH - 2 * PAD

        self.cv = tk.Canvas(parent, width=self.w, height=self.h,
                            bg=BG, highlightthickness=0, bd=0)
        self.cv.pack(fill="x", pady=(0, CARD_GAP))

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

        self.detail_item = self.cv.create_text(
            16, self.h - 13, text="", anchor="w",
            font=app.font_small, fill=MUTED)
        self.delta_item = self.cv.create_text(
            self.w - 16, self.h - 13, text="", anchor="e",
            font=app.font_small, fill=MUTED)
        if self.compact:
            self.cv.itemconfig(self.detail_item, state="hidden")
            self.cv.itemconfig(self.delta_item, state="hidden")

        # Interactions
        app.make_draggable(self.cv)
        self.cv.bind("<Double-Button-1>",
                     lambda _e, m=info.mountpoint: open_in_files(m))
        self.cv.bind("<Button-3>", app.show_menu)
        self.cv.bind("<Enter>", lambda _e: self.cv.itemconfig(self.card_bg, fill=CARD_HOVER))
        self.cv.bind("<Leave>", lambda _e: self.cv.itemconfig(self.card_bg, fill=CARD))

        self.set_data(info)
        self._redraw_bar()

    def set_data(self, info: PartInfo) -> None:
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
        self.prev_used = info.used

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

        self.root = tk.Tk()
        self.root.title("Disk Space Monitor")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", self.pinned)
        try:
            self.root.attributes("-alpha", 0.0)   # start invisible for fade-in
        except tk.TclError:
            pass
        self.root.configure(bg=BORDER)             # acts as 1px outer hairline

        self.font_name = tkfont.Font(family="DejaVu Sans", size=10, weight="bold")
        self.font_pct = tkfont.Font(family="DejaVu Sans", size=12, weight="bold")
        self.font_small = tkfont.Font(family="DejaVu Sans", size=8)
        self.font_title = tkfont.Font(family="DejaVu Sans", size=11, weight="bold")
        self.font_icon = tkfont.Font(family="DejaVu Sans", size=12)

        self._drag = {"x": 0, "y": 0}
        self.cards: dict[str, PartitionCard] = {}
        self._last_keys: tuple[str, ...] = ()

        # 1px border via outer bg; inner holder is the real surface
        self.outer = tk.Frame(self.root, bg=BG)
        self.outer.pack(fill="both", expand=True, padx=1, pady=1)

        self._build_header()
        self._build_menu()

        self.body = tk.Frame(self.outer, bg=BG)
        self.body.pack(fill="both", expand=True, padx=PAD, pady=(PAD, PAD - CARD_GAP))

        self._restore_position()
        self.refresh()
        self._animate()
        self._fade_in(0)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)

    # ---- chrome ---------------------------------------------------------- #
    def _build_header(self) -> None:
        hdr = tk.Frame(self.outer, bg=HEADER_BG, height=HEADER_H)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        title = tk.Label(hdr, text="  💽  Disk Monitor", bg=HEADER_BG, fg=FG,
                         font=self.font_title)
        title.pack(side="left", padx=(6, 0))

        self.btn_close = self._chrome_btn(hdr, "✕", self.quit, "#ff6b6b")
        self.btn_compact = self._chrome_btn(hdr, "▭", self.toggle_compact, MUTED)
        self.btn_pin = self._chrome_btn(
            hdr, "📌", self.toggle_pin, ACCENT if self.pinned else MUTED)

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

    def _build_menu(self) -> None:
        self.menu = tk.Menu(self.root, tearoff=0, bg=CARD, fg=FG,
                            activebackground=ACCENT, activeforeground=BG, bd=0)
        self.menu.add_command(label="Refresh now", command=self.refresh)
        speed = tk.Menu(self.menu, tearoff=0, bg=CARD, fg=FG,
                        activebackground=ACCENT, activeforeground=BG)
        for label, ms in (("Fast (0.5s)", 500), ("Normal (1.5s)", 1500),
                          ("Relaxed (3s)", 3000), ("Slow (5s)", 5000)):
            speed.add_command(label=label, command=lambda m=ms: self.set_interval(m))
        self.menu.add_cascade(label="Update speed", menu=speed)
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

    # ---- toggles --------------------------------------------------------- #
    def toggle_pin(self) -> None:
        self.pinned = not self.pinned
        self.root.attributes("-topmost", self.pinned)
        self.btn_pin.config(fg=ACCENT if self.pinned else MUTED)

    def toggle_compact(self) -> None:
        self.compact = not self.compact
        self._last_keys = ()   # force rebuild at new height
        self.refresh()

    def set_interval(self, ms: int) -> None:
        self.interval = ms

    # ---- geometry / fx --------------------------------------------------- #
    def _restore_position(self) -> None:
        x, y = self.cfg.get("x"), self.cfg.get("y")
        self.root.geometry(f"+{int(x)}+{int(y)}" if x is not None else "+60+60")

    def _resize(self, n_rows: int) -> None:
        card_h = CARD_H_COMPACT if self.compact else CARD_H
        body_h = (PAD + n_rows * (card_h + CARD_GAP) + (PAD - CARD_GAP)) if n_rows \
            else PAD * 2
        height = 1 + HEADER_H + 3 + body_h + 1
        self.root.geometry(f"{WIDTH}x{height}")

    def _fade_in(self, step: int) -> None:
        target = ALPHA
        val = min(target, step * (target / 12))
        try:
            self.root.attributes("-alpha", val)
        except tk.TclError:
            return
        if val < target:
            self.root.after(16, lambda: self._fade_in(step + 1))

    # ---- loops ----------------------------------------------------------- #
    def refresh(self) -> None:
        parts = scan_partitions()
        keys = tuple(p.mountpoint for p in parts)
        if keys != self._last_keys:
            for c in self.cards.values():
                c.destroy()
            self.cards.clear()
            for info in parts:
                self.cards[info.mountpoint] = PartitionCard(self.body, self, info)
            self._last_keys = keys
            self._resize(len(parts))
        else:
            for info in parts:
                self.cards[info.mountpoint].set_data(info)

        if self.pinned:
            self.root.attributes("-topmost", True)
        self.root.after(self.interval, self.refresh)

    def _animate(self) -> None:
        for c in self.cards.values():
            c.step()
        self.root.after(ANIM_MS, self._animate)

    # ---- shutdown -------------------------------------------------------- #
    def quit(self) -> None:
        self.cfg.update({
            "x": self.root.winfo_x(), "y": self.root.winfo_y(),
            "interval_ms": self.interval, "pinned": self.pinned,
            "compact": self.compact,
        })
        save_config(self.cfg)
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    DiskMonitorApp().run()


if __name__ == "__main__":
    main()
