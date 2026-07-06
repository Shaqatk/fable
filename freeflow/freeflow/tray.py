"""System tray icon: open dashboard, pause/resume, quit."""

from __future__ import annotations

from PIL import Image, ImageDraw
import pystray


def _make_icon(paused: bool = False) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    color = (122, 162, 247, 255) if not paused else (100, 100, 110, 255)
    # simple microphone glyph
    d.rounded_rectangle([24, 8, 40, 36], radius=8, fill=color)
    d.arc([16, 20, 48, 48], start=0, end=180, fill=color, width=5)
    d.line([32, 48, 32, 56], fill=color, width=5)
    d.line([22, 56, 42, 56], fill=color, width=5)
    return img


class Tray:
    def __init__(self, settings, on_open, on_quit):
        self.settings = settings
        self.on_open = on_open
        self.on_quit = on_quit
        self.icon = pystray.Icon(
            "FreeFlow", _make_icon(), "FreeFlow — voice dictation",
            menu=pystray.Menu(
                pystray.MenuItem("Open FreeFlow", self._open, default=True),
                pystray.MenuItem("Pause dictation", self._toggle_pause,
                                 checked=lambda item: bool(self.settings.get("paused"))),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", self._quit),
            ),
        )

    def _open(self, icon, item) -> None:
        self.on_open()

    def _toggle_pause(self, icon, item) -> None:
        paused = not self.settings.get("paused")
        self.settings.set("paused", paused)
        self.icon.icon = _make_icon(paused)

    def _quit(self, icon, item) -> None:
        self.icon.stop()
        self.on_quit()

    def run_detached(self) -> None:
        self.icon.run_detached()
