"""Microphone capture.

Records 16 kHz mono float32 (what Whisper expects) and reports a live RMS
level so the overlay can draw a waveform.
"""

from __future__ import annotations

import threading
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16_000


class Recorder:
    def __init__(self, device: Optional[int] = None,
                 level_callback: Optional[Callable[[float], None]] = None):
        self.device = device
        self.level_callback = level_callback
        self._chunks: list[np.ndarray] = []
        self._stream: Optional[sd.InputStream] = None
        self._lock = threading.Lock()

    @property
    def recording(self) -> bool:
        return self._stream is not None

    def start(self) -> None:
        with self._lock:
            if self._stream is not None:
                return
            self._chunks = []
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                device=self.device,
                blocksize=1600,  # 100 ms blocks -> smooth level updates
                callback=self._on_block,
            )
            self._stream.start()

    def _on_block(self, indata, frames, time_info, status) -> None:
        mono = indata[:, 0].copy()
        self._chunks.append(mono)
        if self.level_callback is not None:
            rms = float(np.sqrt(np.mean(mono ** 2)))
            self.level_callback(min(1.0, rms * 12))  # scaled for display

    def stop(self) -> np.ndarray:
        """Stop and return the recorded audio as one float32 array."""
        with self._lock:
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
                self._stream = None
        if not self._chunks:
            return np.zeros(0, dtype=np.float32)
        audio = np.concatenate(self._chunks)
        self._chunks = []
        return audio


def list_input_devices() -> list[dict]:
    """Input devices for the settings UI."""
    devices = []
    try:
        default_in = sd.default.device[0]
    except Exception:
        default_in = None
    for idx, dev in enumerate(sd.query_devices()):
        if dev.get("max_input_channels", 0) > 0:
            devices.append({
                "index": idx,
                "name": dev["name"],
                "default": idx == default_in,
            })
    return devices
