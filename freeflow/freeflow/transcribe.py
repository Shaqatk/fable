"""Local speech-to-text via faster-whisper (CTranslate2, int8 CPU).

The model is lazy-loaded on first use and cached; switching model size in
settings triggers a reload. Whisper gives us punctuation, casing, and
automatic language detection across ~100 languages out of the box.
"""

from __future__ import annotations

import threading
from typing import Optional

import numpy as np


class Transcriber:
    def __init__(self, model_size: str = "base", language: str = "auto"):
        self.model_size = model_size
        self.language = language
        self._model = None
        self._lock = threading.Lock()

    def configure(self, model_size: str, language: str) -> None:
        with self._lock:
            if model_size != self.model_size:
                self._model = None  # force reload with new size
            self.model_size = model_size
            self.language = language

    def _ensure_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel  # heavy import, keep lazy
            self._model = WhisperModel(
                self.model_size, device="cpu", compute_type="int8"
            )
        return self._model

    def preload(self) -> None:
        """Warm the model in the background so the first dictation is fast."""
        with self._lock:
            self._ensure_model()

    def transcribe(self, audio: np.ndarray) -> tuple[str, Optional[str]]:
        """Return (text, detected_language). audio: float32 mono @16 kHz."""
        if audio.size < 1600:  # <0.1 s — nothing useful
            return "", None
        with self._lock:
            model = self._ensure_model()
            language = None if self.language == "auto" else self.language
            segments, info = model.transcribe(
                audio,
                language=language,
                beam_size=1,
                vad_filter=True,
                condition_on_previous_text=False,
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
            return text, getattr(info, "language", None)
