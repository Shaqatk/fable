"""Global hotkey handling.

Reproduces Wispr Flow's interaction model:
- Hold the hotkey (default Ctrl+Win)  -> push-to-talk: record while held.
- Tap it briefly                      -> toggle hands-free recording on/off.
- Command hotkey (default Ctrl+Win+Alt) -> hold to speak an instruction that
  rewrites the currently selected text (needs an LLM API key).

Built on the `keyboard` library's low-level hooks so it works in any app.
"""

from __future__ import annotations

import threading
import time
from typing import Callable

import keyboard

_MOD_ALIASES = {
    "ctrl": {"ctrl", "left ctrl", "right ctrl"},
    "windows": {"windows", "left windows", "right windows"},
    "alt": {"alt", "left alt", "right alt", "alt gr"},
    "shift": {"shift", "left shift", "right shift"},
}


def _expand(combo: str) -> list[set[str]]:
    """'ctrl+windows' -> [ {ctrl variants}, {windows variants} ]"""
    parts = [p.strip().lower() for p in combo.split("+") if p.strip()]
    return [_MOD_ALIASES.get(p, {p}) for p in parts]


class HotkeyManager:
    """Watches key state and drives the dictation controller.

    Callbacks (all invoked from the hook thread):
      on_ptt_start()            hotkey went down
      on_ptt_stop(tap: bool)    hotkey released; tap=True if it was a quick tap
      on_command_start() / on_command_stop()  for command mode
    """

    def __init__(self, settings,
                 on_ptt_start: Callable[[], None],
                 on_ptt_stop: Callable[[bool], None],
                 on_command_start: Callable[[], None],
                 on_command_stop: Callable[[], None]):
        self.settings = settings
        self.on_ptt_start = on_ptt_start
        self.on_ptt_stop = on_ptt_stop
        self.on_command_start = on_command_start
        self.on_command_stop = on_command_stop

        self._down: set[str] = set()
        self._ptt_active = False
        self._cmd_active = False
        self._ptt_down_at = 0.0
        self._lock = threading.Lock()
        self._hook = None

    # -- key state ---------------------------------------------------------
    def _canonical(self, name: str) -> str:
        name = (name or "").lower()
        for canon, variants in _MOD_ALIASES.items():
            if name in variants:
                return canon
        return name

    def _is_combo_pressed(self, combo: str) -> bool:
        if not combo:
            return False
        pressed = {self._canonical(k) for k in self._down}
        for group in _expand(combo):
            if not (pressed & {self._canonical(g) for g in group}):
                return False
        return True

    # -- hook --------------------------------------------------------------
    def start(self) -> None:
        self._hook = keyboard.hook(self._on_event)

    def stop(self) -> None:
        if self._hook is not None:
            keyboard.unhook(self._hook)
            self._hook = None

    def _on_event(self, event) -> None:
        name = self._canonical(event.name)
        with self._lock:
            if event.event_type == "down":
                self._down.add(name)
            else:
                self._down.discard(name)

            if self.settings.get("paused"):
                self._end_active_modes()
                return

            cmd_combo = self.settings.get("command_hotkey")
            ptt_combo = self.settings.get("hotkey")

            cmd_pressed = self._is_combo_pressed(cmd_combo)
            ptt_pressed = self._is_combo_pressed(ptt_combo) and not cmd_pressed

            # Command mode takes priority (it's a superset combo).
            if cmd_pressed and not self._cmd_active:
                if self._ptt_active:
                    self._ptt_active = False
                    self.on_ptt_stop(True)  # treat as cancelled tap
                self._cmd_active = True
                self.on_command_start()
            elif not cmd_pressed and self._cmd_active:
                self._cmd_active = False
                self.on_command_stop()

            if self._cmd_active:
                return

            if ptt_pressed and not self._ptt_active:
                self._ptt_active = True
                self._ptt_down_at = time.monotonic()
                self.on_ptt_start()
            elif not ptt_pressed and self._ptt_active:
                self._ptt_active = False
                held = time.monotonic() - self._ptt_down_at
                tap = held < float(self.settings.get("tap_threshold") or 0.35)
                self.on_ptt_stop(tap)

    def _end_active_modes(self) -> None:
        if self._ptt_active:
            self._ptt_active = False
            self.on_ptt_stop(True)
        if self._cmd_active:
            self._cmd_active = False
            self.on_command_stop()
