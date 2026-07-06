"""Orchestrates the dictation pipeline.

hotkey -> record (+ live transcript preview) -> transcribe -> textproc ->
optional LLM polish -> inject at cursor -> history + stats.

Activation modes (settings.activation_mode):
  "hold"   — record only while the hotkey is held; release inserts.
  "toggle" — press starts, press again stops and inserts.
  "smart"  — hold behaves like "hold"; a quick tap locks hands-free (default).

Command mode: copy selection, record spoken instruction, LLM rewrite, paste
replacement over the selection.
"""

from __future__ import annotations

import queue
import threading
import time

from . import inject, textproc
from .audio import Recorder, SAMPLE_RATE
from .config import Settings
from .history import History
from .overlay import Overlay
from .polish import Polisher
from .transcribe import Transcriber

PREVIEW_WINDOW_S = 14      # live preview transcribes at most the last N seconds
PREVIEW_MIN_AUDIO_S = 0.7  # don't bother previewing before this much audio


class Controller:
    def __init__(self, settings: Settings, history: History, overlay: Overlay):
        self.settings = settings
        self.history = history
        self.overlay = overlay
        self.transcriber = Transcriber(
            settings.get("model_size"), settings.get("language")
        )
        self.polisher = Polisher(settings)
        self.recorder: Recorder | None = None
        self.handsfree = False
        self._mode = "dictate"  # dictate | command
        self._command_selection = ""
        self._target_app: dict = {}
        self._record_started = 0.0
        self._suppress_release = False  # toggle mode: ignore release after a press
        self._model_ready = False
        self._jobs: queue.Queue = queue.Queue()
        self._worker = threading.Thread(target=self._work_loop, name="pipeline", daemon=True)
        self._worker.start()
        self.status_message = "Loading speech model…"
        threading.Thread(target=self._preload, name="preload", daemon=True).start()

    def _preload(self) -> None:
        try:
            self.transcriber.preload()
            self._model_ready = True
            self.status_message = "Ready"
        except Exception as exc:
            self.status_message = f"Model load failed: {exc}"
            self.overlay.flash("Speech model failed to load — check your internet connection", 4000)

    def apply_settings(self) -> None:
        """Called after settings change from the dashboard."""
        self.transcriber.configure(
            self.settings.get("model_size"), self.settings.get("language")
        )
        self.overlay.set_enabled(bool(self.settings.get("show_overlay")))

    # -- hotkey callbacks (from hook thread) ---------------------------------
    def on_ptt_start(self) -> None:
        mode = self.settings.get("activation_mode")
        if mode == "toggle":
            if self.recorder is not None:
                self._suppress_release = True
                self._finish_recording()
            else:
                self._suppress_release = False
                self._begin_recording("dictate")
            return
        if self.handsfree:
            return  # smart mode: already recording; the release handler decides
        self._begin_recording("dictate")

    def on_ptt_stop(self, tap: bool) -> None:
        mode = self.settings.get("activation_mode")
        if mode == "toggle":
            return  # everything happens on key-down in toggle mode
        if mode == "hold":
            self._finish_recording()
            return
        # smart (default): hold = PTT, quick tap = hands-free lock
        if self.handsfree:
            self.handsfree = False
            self._finish_recording()
            return
        if tap:
            self.handsfree = True
            self.overlay.show("handsfree")
            return
        self._finish_recording()

    def on_command_start(self) -> None:
        selection = inject.copy_selection()
        if not selection:
            self.overlay.flash("Select text first, then hold the command hotkey")
            return
        if not self.polisher.command_available:
            self.overlay.flash("Command mode needs an API key (Settings → AI)")
            return
        self._command_selection = selection
        self._begin_recording("command")

    def on_command_stop(self) -> None:
        if self._mode == "command" and self.recorder is not None:
            self._finish_recording()

    # -- recording lifecycle --------------------------------------------------
    def _begin_recording(self, mode: str) -> None:
        if self.recorder is not None:
            return
        self._mode = mode
        self._target_app = inject.get_foreground_app()
        self._record_started = time.monotonic()
        try:
            recorder = Recorder(
                device=self.settings.get("input_device"),
                level_callback=self.overlay.set_level,
            )
            recorder.start()
            self.recorder = recorder
            self.overlay.show("listening" if mode == "dictate" else "handsfree")
            if mode == "dictate" and self.settings.get("live_preview"):
                threading.Thread(
                    target=self._preview_loop, args=(recorder,),
                    name="preview", daemon=True,
                ).start()
        except Exception as exc:
            self.recorder = None
            self.overlay.flash(f"Microphone error: {exc}", 3000)

    def _preview_loop(self, recorder: Recorder) -> None:
        """While `recorder` is live, periodically transcribe what we have so
        far and stream it to the overlay. Whisper isn't a streaming model, so
        this re-transcribes the (bounded) tail — the transcribe call itself
        provides natural throttling on slower machines."""
        if not self._model_ready:
            return
        time.sleep(0.8)
        while self.recorder is recorder:
            snap = recorder.snapshot()
            if snap.size >= SAMPLE_RATE * PREVIEW_MIN_AUDIO_S:
                tail = snap[-SAMPLE_RATE * PREVIEW_WINDOW_S:]
                try:
                    text, _ = self.transcriber.transcribe(tail)
                except Exception:
                    return
                if self.recorder is recorder and text:
                    prefix = "… " if snap.size > tail.size else ""
                    self.overlay.set_partial(prefix + text)
            time.sleep(0.25)

    def _finish_recording(self) -> None:
        if self.recorder is None:
            return
        recorder, self.recorder = self.recorder, None
        data = recorder.stop()
        duration = time.monotonic() - self._record_started
        if data.size < SAMPLE_RATE * 0.25:  # too short to contain speech
            self.overlay.hide()
            return
        self.overlay.show("processing", "Transcribing…")
        self._jobs.put((self._mode, data, duration, self._target_app,
                        self._command_selection))
        self._command_selection = ""

    def cancel(self) -> None:
        if self.recorder is not None:
            recorder, self.recorder = self.recorder, None
            recorder.stop()
        self.handsfree = False
        self.overlay.hide()

    # -- worker ---------------------------------------------------------------
    def _work_loop(self) -> None:
        while True:
            mode, data, duration, app, selection = self._jobs.get()
            try:
                self._process(mode, data, duration, app, selection)
            except Exception as exc:
                self.overlay.flash(f"Error: {exc}", 3000)

    def _process(self, mode, data, duration, app, selection) -> None:
        text, language = self.transcriber.transcribe(data)
        if not text:
            self.overlay.flash("Didn't catch that")
            return

        if mode == "command":
            self.overlay.show("processing", "Applying edit…")
            result = self.polisher.run_command(selection, text)
            if not result:
                self.overlay.flash("Command failed — text unchanged", 2500)
                return
            self.overlay.show_final(result)
            inject.insert_text(result)
            self.history.add(result, duration, app.get("exe", ""), language or "")
            return

        text = textproc.process(text, self.settings.all())
        if self.polisher.available:
            self.overlay.show("processing", "Polishing…")
            text = self.polisher.polish(text, app)
        if not text:
            self.overlay.flash("Didn't catch that")
            return

        # Save first so nothing is lost even if injection fails.
        self.history.add(text, duration, app.get("exe", ""), language or "")
        self.overlay.show_final(text)
        if not inject.insert_text(text):
            self.overlay.flash("Couldn't paste — text copied to clipboard", 3000)
