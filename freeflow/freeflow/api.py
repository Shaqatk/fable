"""JS bridge exposed to the dashboard webview (window.pywebview.api.*).

NOTE: pywebview recursively exposes every PUBLIC attribute of this object to
JavaScript. Collaborators must stay underscore-private, otherwise the bridge
walks into controller -> overlay -> native window COM objects and breaks.
"""

from __future__ import annotations

from . import audio


class Api:
    def __init__(self, settings, history, controller):
        self._settings = settings
        self._history = history
        self._controller = controller

    # -- home ----------------------------------------------------------------
    def get_state(self) -> dict:
        return {
            "settings": self._settings.all(),
            "stats": self._history.stats(),
            "status": self._controller.status_message,
        }

    def get_history(self) -> list:
        return self._history.recent(100)

    def delete_history(self, row_id: int) -> None:
        self._history.delete(int(row_id))

    # -- settings --------------------------------------------------------------
    def save_settings(self, values: dict) -> dict:
        self._settings.update(values)
        self._controller.apply_settings()
        return self._settings.all()

    def list_microphones(self) -> list:
        return audio.list_input_devices()

    # -- dictionary / snippets -------------------------------------------------
    def add_dictionary(self, src: str, dst: str) -> list:
        rules = self._settings.get("dictionary")
        rules.append({"from": src.strip(), "to": (dst or src).strip()})
        self._settings.set("dictionary", rules)
        return rules

    def remove_dictionary(self, index: int) -> list:
        rules = self._settings.get("dictionary")
        if 0 <= index < len(rules):
            rules.pop(index)
        self._settings.set("dictionary", rules)
        return rules

    def add_snippet(self, trigger: str, text: str) -> list:
        snippets = self._settings.get("snippets")
        snippets.append({"trigger": trigger.strip(), "text": text})
        self._settings.set("snippets", snippets)
        return snippets

    def remove_snippet(self, index: int) -> list:
        snippets = self._settings.get("snippets")
        if 0 <= index < len(snippets):
            snippets.pop(index)
        self._settings.set("snippets", snippets)
        return snippets
