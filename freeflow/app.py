"""FreeFlow — local-first voice dictation for Windows.

Hold Ctrl+Win anywhere, speak, release: polished text appears at your cursor.
Run with pythonw.exe for no console window, or python.exe for logs.
"""

from __future__ import annotations

import sys
from pathlib import Path

import webview

from freeflow.api import Api
from freeflow.config import Settings
from freeflow.controller import Controller
from freeflow.history import History
from freeflow.hotkeys import HotkeyManager
from freeflow.overlay import Overlay
from freeflow.tray import Tray

UI_PATH = Path(__file__).parent / "freeflow" / "ui" / "index.html"


def main() -> None:
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
        "FreeFlow", str(UI_PATH), js_api=api,
        width=1080, height=760, min_size=(880, 620),
        background_color="#0e0e14",
    )

    def show_window() -> None:
        try:
            window.show()
            window.restore()
        except Exception:
            pass

    def quit_app() -> None:
        try:
            hotkeys.stop()
            controller.cancel()
            window.destroy()
        finally:
            sys.exit(0)

    tray = Tray(settings, on_open=show_window, on_quit=quit_app)
    tray.run_detached()

    # Closing the window hides it to the tray instead of quitting.
    def on_closing():
        window.hide()
        return False

    window.events.closing += on_closing

    webview.start()  # blocks on the GUI loop
    tray.icon.stop()


if __name__ == "__main__":
    main()
