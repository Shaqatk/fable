"""FreeFlow — local-first voice dictation for Windows.

Hold Ctrl+Win anywhere, speak, release: polished text appears at your cursor.
Run with pythonw.exe for no console window, or python.exe for logs.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import webview

from freeflow.api import Api
from freeflow.config import Settings
from freeflow.controller import Controller
from freeflow.history import History
from freeflow.hotkeys import HotkeyManager
from freeflow import overlay as overlay_mod
from freeflow.overlay import Overlay
from freeflow import single_instance
from freeflow.tray import Tray
from freeflow.winicon import apply_window_icon

UI_PATH = Path(__file__).parent / "freeflow" / "ui" / "index.html"
OVERLAY_PATH = Path(__file__).parent / "freeflow" / "ui" / "overlay.html"
WINDOW_TITLE = "FreeFlow"


def main() -> None:
    if not single_instance.acquire_or_notify_show():
        sys.exit(0)
    if not single_instance.claim_primary():
        sys.exit(0)

    settings = Settings()
    history = History()
    overlay = Overlay(enabled=bool(settings.get("show_overlay")))
    controller = Controller(settings, history, overlay)

    hotkeys = HotkeyManager(
        settings,
        on_ptt_start=controller.on_ptt_start,
        on_ptt_stop=controller.on_ptt_stop,
        on_command_start=controller.on_command_start,
        on_command_stop=controller.on_command_stop,
    )
    hotkeys.start()

    api = Api(settings, history, controller)
    window = webview.create_window(
        WINDOW_TITLE, str(UI_PATH), js_api=api,
        width=1080, height=760, min_size=(880, 620),
        background_color="#0e0e14",
    )

    ox, oy = overlay_mod.screen_position()
    overlay_window = webview.create_window(
        overlay_mod.WINDOW_TITLE, str(OVERLAY_PATH),
        width=overlay_mod.W, height=overlay_mod.H, x=ox, y=oy,
        frameless=True, on_top=True, resizable=False, focus=False,
        hidden=True, background_color="#1a1a1f",
    )
    overlay.attach(overlay_window)

    def show_window() -> None:
        try:
            window.show()
            window.restore()
        except Exception:
            pass

    single_instance.register_show_handler(show_window)

    def quit_app() -> None:
        try:
            hotkeys.stop()
            controller.cancel()
            single_instance.release()
            try:
                window.destroy()
            except Exception:
                pass
            try:
                tray.icon.stop()
            except Exception:
                pass
        finally:
            os._exit(0)

    tray = Tray(settings, on_open=show_window, on_quit=quit_app)
    tray.run_detached()

    # Closing the window hides it to the tray instead of quitting.
    def on_closing():
        window.hide()
        return False

    window.events.closing += on_closing

    def init_native() -> None:
        overlay.init_native()
        apply_window_icon(WINDOW_TITLE)

    webview.start(init_native)  # blocks on the GUI loop
    tray.icon.stop()


if __name__ == "__main__":
    main()
