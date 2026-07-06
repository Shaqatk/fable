"""Apply the FreeFlow icon to native Win32 windows (taskbar / title bar)."""

from __future__ import annotations

import ctypes
import time
from pathlib import Path

user32 = ctypes.windll.user32

ICON_PATH = Path(__file__).parent / "assets" / "mic.ico"

WM_SETICON = 0x0080
ICON_SMALL = 0
ICON_BIG = 1
LR_LOADFROMFILE = 0x0010
IMAGE_ICON = 1


def apply_window_icon(title: str, ico_path: Path | None = None, retries: int = 60) -> None:
    path = ico_path or ICON_PATH
    if not path.is_file():
        return

    hwnd = 0
    for _ in range(retries):
        hwnd = user32.FindWindowW(None, title)
        if hwnd:
            break
        time.sleep(0.1)
    if not hwnd:
        return

    hicon = user32.LoadImageW(
        0, str(path.resolve()), IMAGE_ICON, 0, 0, LR_LOADFROMFILE
    )
    if not hicon:
        return

    user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon)
    user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon)
