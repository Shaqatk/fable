"""System tray icon: open dashboard, pause/resume, quit."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageEnhance
import pystray

ICON_PNG = Path(__file__).parent / "assets" / "mic.png"
_TRAY_SIZE = 64
_base_icon: Image.Image | None = None


def _load_base_icon() -> Image.Image:
    global _base_icon
    if _base_icon is None:
        img = Image.open(ICON_PNG).convert("RGBA")
        _base_icon = img.resize((_TRAY_SIZE, _TRAY_SIZE), Image.Resampling.LANCZOS)
    return _base_icon.copy()


def _make_icon(paused: bool = False) -> Image.Image:
    img = _load_base_icon()
    if not paused:
        return img

    gray = ImageEnhance.Color(img).enhance(0.0)
    return ImageEnhance.Brightness(gray).enhance(0.6)


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
        self.on_quit()

    def run_detached(self) -> None:
        self.icon.run_detached()
