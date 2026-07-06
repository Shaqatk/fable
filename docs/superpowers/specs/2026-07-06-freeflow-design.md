# FreeFlow — AI Voice Dictation for Windows (Wispr Flow functional clone)

Date: 2026-07-06
Status: Approved for implementation (autonomous session; user directed "build start to finish, don't stop")

## Goal

A native Windows dictation app that reproduces the Wispr Flow experience: hold a hotkey
anywhere in Windows, speak naturally, release — clean, formatted text appears at the cursor
in whatever app has focus. Original branding ("FreeFlow"); no Wispr assets or code are copied.

## Researched behavior being cloned (wisprflow.ai + independent reviews)

- Push-to-talk: hold **Ctrl+Win** (Flow's Windows default), release to insert. Quick tap = hands-free
  toggle mode (tap again to stop and insert).
- Floating pill/bar at bottom-center showing live mic levels while recording; can be disabled.
- AI auto-edits: filler-word removal ("um", "uh", "like, you know"), punctuation and casing,
  self-corrections; spoken layout commands ("new line", "new paragraph").
- Personal dictionary: custom names/jargon plus "replace X with Y" rules.
- Snippets: spoken trigger phrase expands to stored text (e.g. "my calendar link").
- 100+ languages with auto-detect (Whisper provides this natively).
- Command mode: with text selected, a second hotkey lets you speak an instruction
  ("make this friendlier") and the selection is rewritten in place.
- Tone awareness: output tone adapts to the foreground app (email vs chat vs code editor).
- Dashboard: history of dictations with copy, stats (words dictated, avg WPM, time saved vs
  typing at 45 WPM), dictionary/snippet managers, settings.
- Tray icon; runs in background.

## Architecture decision

**Python 3.13** (installed) over Electron/C#: the entire hard core of this app — global
key-hold hooks, mic capture, local speech-to-text, synthetic keystrokes — has mature Python
libraries; Node lacks a dependable local ASR path and no .NET SDK is installed.

Transcription is **local and private by default** via `faster-whisper` (CTranslate2 Whisper,
int8 on CPU). No account or API key required — unlike Wispr Flow's cloud ASR. An optional
LLM "polish" pass and command mode use a user-supplied Anthropic or OpenAI key.

### Components (freeflow/freeflow/)

| Module | Responsibility |
|---|---|
| `config.py` | Settings JSON in `%APPDATA%\FreeFlow`, defaults, load/save |
| `audio.py` | `Recorder`: sounddevice InputStream, 16 kHz mono float32, live RMS level callback |
| `transcribe.py` | `Transcriber`: lazy-loads faster-whisper model (size/language from settings) |
| `textproc.py` | Pure-text pipeline: fillers, spoken commands, dictionary, snippets, spacing/casing |
| `polish.py` | Optional LLM cleanup + command-mode rewrite (Anthropic/OpenAI, stdlib HTTP) |
| `inject.py` | Clipboard-preserving paste (Ctrl+V) at cursor; foreground app detection (ctypes) |
| `hotkeys.py` | `keyboard` hook: hold≥250 ms = PTT, tap = hands-free toggle; command-mode hotkey |
| `overlay.py` | tkinter pill, bottom-center, topmost, WS_EX_NOACTIVATE (never steals focus), waveform |
| `history.py` | SQLite history + aggregate stats |
| `api.py` | pywebview JS bridge for the dashboard |
| `tray.py` | pystray icon: show dashboard, pause, quit |
| `app.py` | Wires everything; pywebview main loop |

### Dataflow

hotkey down → overlay shows + Recorder starts → hotkey up → Recorder stops →
Transcriber (worker thread) → textproc pipeline → (optional polish w/ foreground-app tone) →
inject at cursor → history row + stats. Snippet triggers and dictionary rules apply in textproc.

### Threading

pywebview owns the main thread; tkinter overlay runs its whole lifecycle in one dedicated
thread (queue-fed); keyboard hooks, audio callbacks, transcription worker, and pystray each
run on their own threads. Cross-thread communication is via `queue.Queue` only.

### Error handling

Model download/load failures surface in overlay + dashboard toast; injection failures fall
back to leaving text on the clipboard with a notification; every dictation is saved to
history before injection so nothing is ever lost.

### Testing

- Unit tests (pytest) for `textproc` — the pure logic core.
- End-to-end ASR smoke test: Windows built-in TTS (`System.Speech`) synthesizes a known WAV;
  Transcriber must return the phrase.
- Manual/scripted smoke launch of the full app.

## Non-goals (v1)

Mobile apps, cross-device sync, accounts/billing, whisper-mode (low-voice model), auto-updates.
