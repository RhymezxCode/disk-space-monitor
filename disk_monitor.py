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
# Theme (Dracula-inspired)                                                     #
# --------------------------------------------------------------------------- #
BG = "#1e1f29"
CARD = "#282a36"
HEADER_BG = "#21222c"
FG = "#f8f8f2"
MUTED = "#9aa0b5"
TRACK = "#44475a"
ACCENT = "#bd93f9"

GREEN = "#50fa7b"
YELLOW = "#f1fa8c"
ORANGE = "#ffb86c"
RED = "#ff5555"

ALPHA = 0.93           # window opacity (0..1)
WIDTH = 330            # widget width in px
ROW_H = 60             # px per partition row
HEADER_H = 34          # px header height
PAD = 10
BAR_H = 9              # progress bar thickness

DEFAULT_INTERVAL_MS = 1500   # refresh cadence

CONFIG_DIR = os.path.join(
    os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
    "disk-space-monitor",
)
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

# Filesystem types that are never interesting to a human watching disk space.
SKIP_FSTYPES = {
    "squashfs", "devtmpfs", "tmpfs", "devpts", "sysfs", "proc", "cgroup",
    "cgroup2", "overlay", "mqueue", "debugfs", "tracefs", "securityfs",
    "pstore", "autofs", "configfs", "fusectl", "ramfs", "hugetlbfs",
    "binfmt_misc", "efivarfs", "bpf", "nsfs", "none", "",
}
# Mount points under these prefixes are system plumbing, not user storage.
SKIP_PREFIXES = ("/snap", "/sys", "/proc", "/run", "/dev")


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def human_bytes(n: float) -> str:
    """Format a byte count as a short human-readable string."""
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if abs(n) < 1024 or unit == "PB":
            if unit == "B":
                return f"{n:.0f} B"
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def usage_color(pct: float) -> str:
    if pct >= 93:
        return RED
    if pct >= 85:
        return ORANGE
    if pct >= 70:
        return YELLOW
    return GREEN


def pretty_name(mountpoint: str) -> str:
    if mountpoint == "/":
        return "Root  (/)"
    return mountpoint


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
    total: int
    used: int
    free: int
    percent: float


def scan_partitions() -> list[PartInfo]:
    """Return the list of real, user-facing partitions with current usage."""
    out: list[PartInfo] = []
    seen: set[str] = set()
    for part in psutil.disk_partitions(all=False):
        mp = part.mountpoint
        if part.fstype in SKIP_FSTYPES:
            continue
        if any(mp == p or mp.startswith(p + "/") or mp == p for p in SKIP_PREFIXES):
            continue
        if mp in seen:
            continue
        try:
            u = psutil.disk_usage(mp)
        except (PermissionError, OSError):
            continue
        seen.add(mp)
        out.append(
            PartInfo(mp, part.device, u.total, u.used, u.free, u.percent)
        )
    out.sort(key=lambda p: (p.mountpoint != "/", p.mountpoint))
    return out


# --------------------------------------------------------------------------- #
# A single partition row                                                       #
# --------------------------------------------------------------------------- #
class PartitionRow:
    def __init__(self, parent: tk.Widget, app: "DiskMonitorApp", info: PartInfo):
        self.app = app
        self.mountpoint = info.mountpoint
        self.prev_used = info.used

        self.frame = tk.Frame(parent, bg=CARD)
        self.frame.pack(fill="x", padx=PAD, pady=(0, 8))

        top = tk.Frame(self.frame, bg=CARD)
        top.pack(fill="x")

        self.name_lbl = tk.Label(
            top, text=pretty_name(info.mountpoint), bg=CARD, fg=FG,
            font=app.font_bold, anchor="w",
        )
        self.name_lbl.pack(side="left")

        self.delta_lbl = tk.Label(
            top, text="", bg=CARD, fg=MUTED, font=app.font_small, anchor="e",
        )
        self.delta_lbl.pack(side="right")

        self.pct_lbl = tk.Label(
            top, text="", bg=CARD, fg=FG, font=app.font_bold, anchor="e",
        )
        self.pct_lbl.pack(side="right", padx=(0, 8))

        self.bar = tk.Canvas(
            self.frame, height=BAR_H, bg=TRACK, highlightthickness=0, bd=0,
        )
        self.bar.pack(fill="x", pady=(5, 4))
        self._bar_rect = self.bar.create_rectangle(0, 0, 0, BAR_H, width=0, fill=GREEN)

        self.detail_lbl = tk.Label(
            self.frame, text="", bg=CARD, fg=MUTED, font=app.font_small, anchor="w",
        )
        self.detail_lbl.pack(fill="x")

        # Drag the whole widget from any non-button surface; double-click opens.
        for w in (self.frame, top, self.name_lbl, self.detail_lbl):
            app.make_draggable(w)
            w.bind("<Double-Button-1>", lambda _e, m=info.mountpoint: open_in_files(m))
            w.bind("<Button-3>", app.show_menu)

        self.update(info)

    def update(self, info: PartInfo) -> None:
        color = usage_color(info.percent)
        self.pct_lbl.config(text=f"{info.percent:.0f}%", fg=color)

        width = max(self.bar.winfo_width(), 1)
        fill_w = int(width * min(info.percent, 100) / 100)
        self.bar.coords(self._bar_rect, 0, 0, fill_w, BAR_H)
        self.bar.itemconfig(self._bar_rect, fill=color)

        if self.app.compact:
            self.detail_lbl.pack_forget()
        else:
            self.detail_lbl.pack(fill="x")
            self.detail_lbl.config(
                text=f"{human_bytes(info.used)} / {human_bytes(info.total)}"
                     f"  ·  {human_bytes(info.free)} free"
            )

        delta = info.used - self.prev_used
        if abs(delta) >= 512 * 1024:  # ignore sub-0.5MB jitter
            if delta > 0:
                self.delta_lbl.config(text=f"▲ {human_bytes(delta)}", fg=ORANGE)
            else:
                self.delta_lbl.config(text=f"▼ {human_bytes(-delta)}", fg=GREEN)
        else:
            self.delta_lbl.config(text="")
        self.prev_used = info.used

    def destroy(self) -> None:
        self.frame.destroy()


def open_in_files(mountpoint: str) -> None:
    try:
        subprocess.Popen(
            ["xdg-open", mountpoint],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except OSError:
        pass


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
        self.root.overrideredirect(True)          # frameless
        self.root.attributes("-topmost", self.pinned)
        try:
            self.root.attributes("-alpha", ALPHA)
        except tk.TclError:
            pass
        self.root.configure(bg=BG)

        self.font_bold = tkfont.Font(family="DejaVu Sans", size=10, weight="bold")
        self.font_small = tkfont.Font(family="DejaVu Sans", size=8)
        self.font_title = tkfont.Font(family="DejaVu Sans", size=10, weight="bold")

        self._drag = {"x": 0, "y": 0}
        self.rows: dict[str, PartitionRow] = {}
        self._tick = 0
        self._last_keys: tuple[str, ...] = ()

        self._build_header()
        self._build_menu()

        self.body = tk.Frame(self.root, bg=BG)
        self.body.pack(fill="both", expand=True, pady=(8, 2))

        self._restore_position()
        self.refresh()
        self.root.protocol("WM_DELETE_WINDOW", self.quit)

    # ---- chrome ---------------------------------------------------------- #
    def _build_header(self) -> None:
        hdr = tk.Frame(self.root, bg=HEADER_BG, height=HEADER_H)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        dot = tk.Label(hdr, text="●", bg=HEADER_BG, fg=ACCENT, font=self.font_title)
        dot.pack(side="left", padx=(PAD, 4))
        title = tk.Label(
            hdr, text="Disk Monitor", bg=HEADER_BG, fg=FG, font=self.font_title,
        )
        title.pack(side="left")

        self.btn_close = self._chrome_btn(hdr, "✕", self.quit, RED)
        self.btn_compact = self._chrome_btn(hdr, "▭", self.toggle_compact, MUTED)
        self.btn_pin = self._chrome_btn(
            hdr, "📌", self.toggle_pin, ACCENT if self.pinned else MUTED
        )

        for w in (hdr, dot, title):
            self.make_draggable(w)
            w.bind("<Button-3>", self.show_menu)

    def _chrome_btn(self, parent, text, cmd, color):
        b = tk.Label(parent, text=text, bg=HEADER_BG, fg=color,
                     font=self.font_title, cursor="hand2")
        b.pack(side="right", padx=6)
        b.bind("<Button-1>", lambda _e: cmd())
        b.bind("<Enter>", lambda _e, x=b: x.config(fg=FG))
        b.bind("<Leave>", lambda _e, x=b, c=color: x.config(fg=c))
        return b

    def _build_menu(self) -> None:
        self.menu = tk.Menu(self.root, tearoff=0, bg=CARD, fg=FG,
                            activebackground=ACCENT, activeforeground=BG, bd=0)
        self.menu.add_command(label="Refresh now", command=self.refresh)
        self.menu.add_separator()
        speed = tk.Menu(self.menu, tearoff=0, bg=CARD, fg=FG,
                        activebackground=ACCENT, activeforeground=BG)
        for label, ms in (("Fast (0.5s)", 500), ("Normal (1.5s)", 1500),
                          ("Relaxed (3s)", 3000), ("Slow (5s)", 5000)):
            speed.add_command(label=label, command=lambda m=ms: self.set_interval(m))
        self.menu.add_cascade(label="Update speed", menu=speed)
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

    # ---- behaviour toggles ---------------------------------------------- #
    def toggle_pin(self) -> None:
        self.pinned = not self.pinned
        self.root.attributes("-topmost", self.pinned)
        self.btn_pin.config(fg=ACCENT if self.pinned else MUTED)

    def toggle_compact(self) -> None:
        self.compact = not self.compact
        self._last_keys = ()  # force rebuild to resize cleanly
        self.refresh()

    def set_interval(self, ms: int) -> None:
        self.interval = ms

    # ---- geometry -------------------------------------------------------- #
    def _restore_position(self) -> None:
        x = self.cfg.get("x")
        y = self.cfg.get("y")
        if x is not None and y is not None:
            self.root.geometry(f"+{int(x)}+{int(y)}")
        else:
            self.root.geometry("+60+60")

    def _resize(self, n_rows: int) -> None:
        row_h = (ROW_H - 16) if self.compact else ROW_H
        height = HEADER_H + 10 + n_rows * row_h + 6
        self.root.geometry(f"{WIDTH}x{height}")

    # ---- the live loop --------------------------------------------------- #
    def refresh(self) -> None:
        # Re-scan every tick: cheap, and it picks up USB drives being
        # plugged/unplugged as well as live usage changes.
        parts = scan_partitions()
        self._tick += 1

        keys = tuple(p.mountpoint for p in parts)
        if keys != self._last_keys:
            for row in self.rows.values():
                row.destroy()
            self.rows.clear()
            for info in parts:
                self.rows[info.mountpoint] = PartitionRow(self.body, self, info)
            self._last_keys = keys
            self._resize(len(parts))
        else:
            for info in parts:
                self.rows[info.mountpoint].update(info)

        if not parts:
            self._resize(0)

        if self.pinned:
            self.root.attributes("-topmost", True)  # re-assert above other windows

        self.root.after(self.interval, self.refresh)

    # ---- shutdown -------------------------------------------------------- #
    def quit(self) -> None:
        self.cfg.update({
            "x": self.root.winfo_x(),
            "y": self.root.winfo_y(),
            "interval_ms": self.interval,
            "pinned": self.pinned,
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
