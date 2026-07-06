"""Insert text at the cursor of whatever app has focus.

Strategy (same as commercial dictation tools): put the text on the clipboard,
send Ctrl+V, then restore the user's previous clipboard. Also exposes
foreground-app detection (used for tone-aware polish) and select-copy for
command mode. Windows-only, via ctypes + the keyboard library.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import time

import keyboard
import pyperclip

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


def get_foreground_app() -> dict:
    """Return {'title': window title, 'exe': process image name} of the focused window."""
    hwnd = user32.GetForegroundWindow()
    title_buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, title_buf, 256)

    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    exe = ""
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if handle:
        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = wt.DWORD(1024)
            if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                exe = buf.value.rsplit("\\", 1)[-1]
        finally:
            kernel32.CloseHandle(handle)
    return {"title": title_buf.value, "exe": exe}


def _release_hotkey_modifiers() -> None:
    """Make sure Ctrl/Win/Alt from the dictation hotkey aren't still held when we paste."""
    for key in ("ctrl", "windows", "alt", "shift"):
        try:
            keyboard.release(key)
        except Exception:
            pass


def insert_text(text: str, restore_clipboard: bool = True) -> bool:
    """Paste `text` at the cursor. Returns True on (apparent) success."""
    if not text:
        return False
    previous = None
    if restore_clipboard:
        try:
            previous = pyperclip.paste()
        except Exception:
            previous = None
    try:
        pyperclip.copy(text)
        _release_hotkey_modifiers()
        time.sleep(0.05)  # let the target app regain modifier state
        keyboard.send("ctrl+v")
        time.sleep(0.15)  # let the paste land before clipboard restore
        if restore_clipboard and previous is not None:
            pyperclip.copy(previous)
        return True
    except Exception:
        # Leave the text on the clipboard as a fallback so nothing is lost.
        try:
            pyperclip.copy(text)
        except Exception:
            pass
        return False


def copy_selection() -> str:
    """Copy the current selection (for command mode). Returns '' if nothing selected."""
    try:
        previous = pyperclip.paste()
    except Exception:
        previous = ""
    try:
        pyperclip.copy("")  # sentinel: detect whether Ctrl+C actually copied
        _release_hotkey_modifiers()
        time.sleep(0.05)
        keyboard.send("ctrl+c")
        time.sleep(0.2)
        selection = pyperclip.paste()
        if not selection:
            pyperclip.copy(previous)
        return selection
    except Exception:
        return ""
