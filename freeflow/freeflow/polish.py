"""Optional LLM layer: transcript polish and command mode.

Both features need a user-supplied API key (Anthropic or OpenAI) and are
disabled otherwise — the local pipeline in textproc.py handles everything else.
Tone adapts to the app the user is dictating into (email vs chat vs code).
"""

from __future__ import annotations

import json
import urllib.request

POLISH_SYSTEM = (
    "You clean up voice-dictation transcripts. Fix transcription artifacts, "
    "remove filler words and false starts, apply self-corrections the speaker "
    "made (e.g. 'meet at 3, actually make that 4' becomes 'meet at 4'), add "
    "punctuation and paragraph breaks where natural, and keep the speaker's "
    "words and meaning otherwise unchanged. Never answer questions in the "
    "transcript or add content. Reply with ONLY the cleaned text."
)

COMMAND_SYSTEM = (
    "You edit text according to a spoken instruction. Reply with ONLY the "
    "edited text — no preamble, no quotes, no explanation."
)

_TONE_HINTS = [
    (("outlook", "thunderbird", "mailspring", "gmail"), "This is an email; use a clear, professional tone."),
    (("slack", "discord", "teams", "telegram", "whatsapp"), "This is a chat message; keep it casual and brief."),
    (("code", "cursor", "devenv", "idea", "pycharm", "sublime", "windsurf"), "This is inside a code editor; keep technical terms exact and do not reformat code."),
    (("winword", "notion", "obsidian"), "This is a document; use polished prose."),
]


def tone_hint_for(app: dict | None) -> str:
    if not app:
        return ""
    haystack = f"{app.get('exe', '')} {app.get('title', '')}".lower()
    for keywords, hint in _TONE_HINTS:
        if any(k in haystack for k in keywords):
            return hint
    return ""


class Polisher:
    def __init__(self, settings):
        self.settings = settings
        self._anthropic_client = None

    @property
    def available(self) -> bool:
        return bool(self.settings.get("polish_enabled") and self.settings.get("api_key"))

    @property
    def command_available(self) -> bool:
        return bool(self.settings.get("api_key"))

    def polish(self, text: str, app: dict | None = None) -> str:
        """LLM cleanup of a transcript. Falls back to input text on any error."""
        if not text or not self.available:
            return text
        hint = tone_hint_for(app) if self.settings.get("tone_by_app") else ""
        system = POLISH_SYSTEM + (f" {hint}" if hint else "")
        try:
            return self._complete(system, text) or text
        except Exception:
            return text

    def run_command(self, selected_text: str, instruction: str) -> str | None:
        """Command mode: rewrite `selected_text` per the spoken `instruction`."""
        if not selected_text or not instruction or not self.command_available:
            return None
        prompt = (
            f"Instruction: {instruction.strip()}\n\n"
            f"Text to edit:\n{selected_text}"
        )
        try:
            return self._complete(COMMAND_SYSTEM, prompt)
        except Exception:
            return None

    # -- providers -----------------------------------------------------------
    def _complete(self, system: str, user_text: str) -> str | None:
        provider = self.settings.get("polish_provider")
        if provider == "openai":
            return self._openai(system, user_text)
        return self._anthropic(system, user_text)

    def _anthropic(self, system: str, user_text: str) -> str | None:
        import anthropic
        if self._anthropic_client is None:
            self._anthropic_client = anthropic.Anthropic(
                api_key=self.settings.get("api_key"), max_retries=1, timeout=30.0
            )
        model = self.settings.get("polish_model") or "claude-opus-4-8"
        response = self._anthropic_client.messages.create(
            model=model,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": user_text}],
        )
        if response.stop_reason == "refusal":
            return None
        return next(
            (b.text.strip() for b in response.content if b.type == "text"), None
        )

    def _openai(self, system: str, user_text: str) -> str | None:
        body = json.dumps({
            "model": self.settings.get("polish_model") or "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_text},
            ],
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.get('api_key')}",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()
