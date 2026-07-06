"""Floating dictation HUD.

A frameless, always-on-top WebView2 card at the bottom-center of the screen —
think macOS dictation HUD: rounded (native Windows 11 DWM corners), dark,
with a 60 fps scrolling waveform and a live transcript of what you're saying.

The webview window itself is created in app.py (pywebview requires windows to
exist before its loop starts); this class drives it. Crucially the window is
shown with SW_SHOWNOACTIVATE and carries WS_EX_NOACTIVATE so it can never
steal focus from the app being dictated into. All UI updates go through
evaluate_js, which pywebview marshals to the GUI thread.
"""

from __future__ import annotations

import ctypes
import json
import threading
import time

W, H = 384, 132
BOTTOM_MARGIN = 68
WINDOW_TITLE = "FreeFlow Overlay"

user32 = ctypes.windll.user32

GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TOPMOST = 0x00000008
SW_HIDE = 0
SW_SHOWNOACTIVATE = 4
HWND_TOPMOST = -1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWCP_ROUND = 2


def screen_position() -> tuple[int, int]:
    sw = user32.GetSystemMetrics(0)
    sh = user32.GetSystemMetrics(1)
    return (sw - W) // 2, sh - H - BOTTOM_MARGIN


class Overlay:
    """States: hidden | listening | handsfree | processing | final | flash."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.window = None
        self._hwnd = 0
        self._state = "hidden"
        self._hide_timer: threading.Timer | None = None
        self._last_level = 0.0

    def attach(self, window) -> None:
        self.window = window

    def init_native(self) -> None:
        """Runs once after the pywebview loop starts: grab the hwnd, make the
        window non-activating + tool-window, round its corners, warm the
        renderer with one invisible show, then hide."""
        hwnd = 0
        for _ in range(60):
            hwnd = user32.FindWindowW(None, WINDOW_TITLE)
            if hwnd:
                break
            time.sleep(0.1)
        if not hwnd:
            return
        self._hwnd = hwnd
        style = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongPtrW(
            hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST
        )
        self._pin_topmost()
        try:
            pref = ctypes.c_int(DWMWCP_ROUND)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.byref(pref), 4
            )
        except Exception:
            pass  # pre-Win11: square corners, still fine
        user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)  # let WebView2 paint once
        time.sleep(0.25)
        user32.ShowWindow(hwnd, SW_HIDE)

    # -- public API (any thread) ----------------------------------------------
    def show(self, state: str, text: str = "") -> None:
        if not self.enabled:
            return
        self._cancel_hide()
        self._state = state
        self._js(f"ov.set({json.dumps({'state': state, 'text': text})})")
        self._set_visible(True)

    def set_level(self, level: float) -> None:
        if self._state not in ("listening", "handsfree"):
            return
        # cheap smoothing on the python side; JS lerps the rest at 60fps
        self._last_level = 0.6 * level + 0.4 * self._last_level
        self._js(f"ov.level({self._last_level:.3f})")

    def set_partial(self, text: str) -> None:
        if self._state in ("listening", "handsfree", "processing"):
            self._js(f"ov.partial({json.dumps(text)})")

    def show_final(self, text: str, ms: int = 1900) -> None:
        self.show("final", text)
        self._schedule_hide(ms)

    def flash(self, text: str, ms: int = 1900) -> None:
        self.show("flash", text)
        self._schedule_hide(ms)

    def hide(self) -> None:
        self._cancel_hide()
        self._state = "hidden"
        self._set_visible(False)
        self._js("ov.reset()")

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        if not enabled:
            self.hide()

    # -- internals -------------------------------------------------------------
    def _set_visible(self, visible: bool) -> None:
        if self._hwnd:
            if visible:
                user32.ShowWindow(self._hwnd, SW_SHOWNOACTIVATE)
                self._pin_topmost()
            else:
                user32.ShowWindow(self._hwnd, SW_HIDE)

    def _pin_topmost(self) -> None:
        """Keep the overlay above normal windows without taking focus."""
        if not self._hwnd:
            return
        user32.SetWindowPos(
            self._hwnd, HWND_TOPMOST, 0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
        )

    def _js(self, code: str) -> None:
        if self.window is None:
            return
        try:
            self.window.evaluate_js(code)
        except Exception:
            pass  # window not ready yet — cosmetic only

    def _schedule_hide(self, ms: int) -> None:
        self._cancel_hide()
        self._hide_timer = threading.Timer(ms / 1000, self.hide)
        self._hide_timer.daemon = True
        self._hide_timer.start()

    def _cancel_hide(self) -> None:
        if self._hide_timer is not None:
            self._hide_timer.cancel()
            self._hide_timer = None
