"""Settings persistence for FreeFlow.

Settings live in %APPDATA%\\FreeFlow\\settings.json. Dictionary and snippets are
part of settings; dictation history lives in a SQLite file next to it.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

APP_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "FreeFlow"

DEFAULTS: dict = {
    # Hotkeys. "ctrl+windows" matches Wispr Flow's Windows default.
    "hotkey": "ctrl+windows",
    "command_hotkey": "ctrl+windows+alt",
    # Hold shorter than this (seconds) counts as a tap => hands-free toggle.
    "tap_threshold": 0.35,
    # How the hotkey behaves:
    #   "hold"   - record only while held; release inserts (walkie-talkie)
    #   "toggle" - press starts, press again stops and inserts
    #   "smart"  - hold = hold-to-talk, quick tap = toggle (both at once)
    "activation_mode": "smart",
    # Live transcript shown under the pill while speaking.
    "live_preview": True,
    # Audio
    "input_device": None,          # None = system default microphone
    # Transcription
    "model_size": "base",          # tiny | base | small | medium | large-v3
    "language": "auto",            # "auto" or ISO code like "en", "es"
    # Text processing
    "remove_fillers": True,
    "spoken_commands": True,       # "new line", "new paragraph"
    "auto_capitalize": True,
    "dictionary": [],              # [{"from": "jira", "to": "Jira"}, ...] ("from" may equal "to" to just teach casing)
    "snippets": [],                # [{"trigger": "my email", "text": "sheharyarhaq@yahoo.com"}, ...]
    # Optional LLM polish
    "polish_enabled": False,
    "polish_provider": "anthropic",  # anthropic | openai
    "polish_model": "",              # empty = provider default
    "api_key": "",
    "tone_by_app": True,
    # UI
    "show_overlay": True,
    "paused": False,
}

_lock = threading.Lock()


class Settings:
    """Thread-safe settings store backed by a JSON file."""

    def __init__(self, path: Path | None = None):
        self.path = path or (APP_DIR / "settings.json")
        self._data = dict(DEFAULTS)
        self.load()

    def load(self) -> None:
        with _lock:
            try:
                on_disk = json.loads(self.path.read_text(encoding="utf-8"))
                self._data = {**DEFAULTS, **on_disk}
            except (FileNotFoundError, json.JSONDecodeError):
                self._data = dict(DEFAULTS)

    def save(self) -> None:
        with _lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8"
            )

    def get(self, key: str):
        with _lock:
            return self._data.get(key, DEFAULTS.get(key))

    def set(self, key: str, value) -> None:
        with _lock:
            self._data[key] = value
        self.save()

    def all(self) -> dict:
        with _lock:
            return dict(self._data)

    def update(self, values: dict) -> None:
        with _lock:
            self._data.update(values)
        self.save()
