"""Floating recording pill.

A small always-on-top rounded pill at the bottom-center of the screen that
shows live mic levels while dictating and a spinner state while transcribing —
the equivalent of Wispr Flow's floating bar.

Crucial detail: the window is created with WS_EX_NOACTIVATE so it NEVER steals
focus — the caret must stay in the app the user is dictating into. All tkinter
calls happen on one dedicated thread; other threads talk to it via a queue.
"""

from __future__ import annotations

import ctypes
import queue
import threading
import tkinter as tk

_TRANSPARENT = "#010203"  # unlikely color used as the transparency key
_BG = "#16161e"
_ACCENT = "#7aa2f7"
_ACCENT_DIM = "#3b4261"
_TEXT = "#c0caf5"

W, H = 240, 56
N_BARS = 17

GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080


class Overlay:
    """States: hidden | listening | handsfree | processing | error(text)."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._q: queue.Queue = queue.Queue()
        self._levels = [0.0] * N_BARS
        self._state = "hidden"
        self._status_text = ""
        self._spin_phase = 0
        self._thread = threading.Thread(target=self._run, name="overlay", daemon=True)
        self._thread.start()

    # -- public API (thread-safe) -------------------------------------------
    def show(self, state: str, text: str = "") -> None:
        self._q.put(("show", state, text))

    def set_level(self, level: float) -> None:
        self._q.put(("level", level, ""))

    def hide(self) -> None:
        self._q.put(("hide", "", ""))

    def flash(self, text: str, ms: int = 1800) -> None:
        self._q.put(("flash", text, ms))

    def set_enabled(self, enabled: bool) -> None:
        self._q.put(("enabled", enabled, ""))

    # -- tkinter thread ------------------------------------------------------
    def _run(self) -> None:
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", _TRANSPARENT)
        self.root.configure(bg=_TRANSPARENT)

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{W}x{H}+{(sw - W) // 2}+{sh - H - 64}")

        self.canvas = tk.Canvas(self.root, width=W, height=H, bg=_TRANSPARENT,
                                highlightthickness=0)
        self.canvas.pack()

        self._apply_noactivate()
        self._tick()
        self.root.mainloop()

    def _apply_noactivate(self) -> None:
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
            style = ctypes.windll.user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongPtrW(
                hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
            )
        except Exception:
            pass  # cosmetic only; never let this kill the overlay

    def _tick(self) -> None:
        try:
            while True:
                kind, a, b = self._q.get_nowait()
                if kind == "show" and self.enabled:
                    self._state, self._status_text = a, b
                    self.root.deiconify()
                    self._apply_noactivate()
                elif kind == "hide":
                    self._state = "hidden"
                    self.root.withdraw()
                elif kind == "level":
                    self._levels.pop(0)
                    self._levels.append(float(a))
                elif kind == "flash" and self.enabled:
                    self._state, self._status_text = "flash", a
                    self.root.deiconify()
                    self._apply_noactivate()
                    self.root.after(int(b), lambda: self._q.put(("hide", "", "")))
                elif kind == "enabled":
                    self.enabled = bool(a)
                    if not self.enabled:
                        self._state = "hidden"
                        self.root.withdraw()
        except queue.Empty:
            pass

        if self._state != "hidden":
            self._draw()
        self.root.after(50, self._tick)

    def _draw(self) -> None:
        c = self.canvas
        c.delete("all")
        self._rounded_rect(c, 2, 2, W - 2, H - 2, 26, fill=_BG)

        if self._state in ("listening", "handsfree"):
            dot = _ACCENT if self._state == "listening" else "#9ece6a"
            c.create_oval(16, H // 2 - 5, 26, H // 2 + 5, fill=dot, outline="")
            x0 = 38
            bar_w, gap = 6, 5
            for i, lvl in enumerate(self._levels):
                h = max(3, lvl * (H - 24))
                x = x0 + i * (bar_w + gap)
                y0 = (H - h) / 2
                c.create_rectangle(x, y0, x + bar_w, y0 + h,
                                   fill=_ACCENT if lvl > 0.04 else _ACCENT_DIM,
                                   outline="")
        elif self._state == "processing":
            self._spin_phase = (self._spin_phase + 25) % 360
            c.create_arc(14, H // 2 - 10, 34, H // 2 + 10, start=self._spin_phase,
                         extent=270, style=tk.ARC, outline=_ACCENT, width=3)
            c.create_text(44, H // 2, anchor="w", fill=_TEXT,
                          font=("Segoe UI", 10), text=self._status_text or "Polishing…")
        elif self._state == "flash":
            c.create_text(W // 2, H // 2, fill=_TEXT, font=("Segoe UI", 10),
                          text=self._status_text, width=W - 30)

    @staticmethod
    def _rounded_rect(c: tk.Canvas, x0, y0, x1, y1, r, **kw) -> None:
        c.create_arc(x0, y0, x0 + 2 * r, y0 + 2 * r, start=90, extent=90, style=tk.PIESLICE, outline="", **kw)
        c.create_arc(x1 - 2 * r, y0, x1, y0 + 2 * r, start=0, extent=90, style=tk.PIESLICE, outline="", **kw)
        c.create_arc(x0, y1 - 2 * r, x0 + 2 * r, y1, start=180, extent=90, style=tk.PIESLICE, outline="", **kw)
        c.create_arc(x1 - 2 * r, y1 - 2 * r, x1, y1, start=270, extent=90, style=tk.PIESLICE, outline="", **kw)
        c.create_rectangle(x0 + r, y0, x1 - r, y1, outline="", **kw)
        c.create_rectangle(x0, y0 + r, x1, y1 - r, outline="", **kw)
