"""JS bridge exposed to the dashboard webview (window.pywebview.api.*)."""

from __future__ import annotations

from . import audio


class Api:
    def __init__(self, settings, history, controller):
        self.settings = settings
        self.history = history
        self.controller = controller

    # -- home ----------------------------------------------------------------
    def get_state(self) -> dict:
        return {
            "settings": self.settings.all(),
            "stats": self.history.stats(),
            "status": self.controller.status_message,
        }

    def get_history(self) -> list:
        return self.history.recent(100)

    def delete_history(self, row_id: int) -> None:
        self.history.delete(int(row_id))

    # -- settings --------------------------------------------------------------
    def save_settings(self, values: dict) -> dict:
        self.settings.update(values)
        self.controller.apply_settings()
        return self.settings.all()

    def list_microphones(self) -> list:
        return audio.list_input_devices()

    # -- dictionary / snippets -------------------------------------------------
    def add_dictionary(self, src: str, dst: str) -> list:
        rules = self.settings.get("dictionary")
        rules.append({"from": src.strip(), "to": (dst or src).strip()})
        self.settings.set("dictionary", rules)
        return rules

    def remove_dictionary(self, index: int) -> list:
        rules = self.settings.get("dictionary")
        if 0 <= index < len(rules):
            rules.pop(index)
        self.settings.set("dictionary", rules)
        return rules

    def add_snippet(self, trigger: str, text: str) -> list:
        snippets = self.settings.get("snippets")
        snippets.append({"trigger": trigger.strip(), "text": text})
        self.settings.set("snippets", snippets)
        return snippets

    def remove_snippet(self, index: int) -> list:
        snippets = self.settings.get("snippets")
        if 0 <= index < len(snippets):
            snippets.pop(index)
        self.settings.set("snippets", snippets)
        return snippets
