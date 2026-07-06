# FreeFlow — local-first AI voice dictation for Windows

Hold **Ctrl+Win** in any app, speak naturally, release — clean, formatted text
appears at your cursor. A functional equivalent of Wispr Flow that runs the
speech recognition **entirely on your own machine** (no account, no
subscription, your voice never leaves your PC).

## Install (one time)

1. Make sure Python 3.10+ is installed ([python.org](https://python.org), check "Add to PATH").
2. Double-click **`install.bat`** — it creates a private environment, installs
   dependencies, and puts a **FreeFlow** shortcut on your Desktop.
3. Launch FreeFlow. The first dictation downloads the speech model (~150 MB),
   so give it a minute; after that everything is instant and offline.

To start it later: the Desktop shortcut, or `FreeFlow.bat`.

## How to use

| Action | How |
|---|---|
| **Push-to-talk** | Click into any text field, **hold Ctrl+Win**, speak, release |
| **Hands-free** | **Tap Ctrl+Win** once to lock the mic; tap again to finish and insert |
| **Command mode** | Select text anywhere, **hold Ctrl+Win+Alt**, say an instruction like *"make this friendlier"* or *"turn this into bullet points"* (needs an API key, see below) |
| **Spoken commands** | Say *"new line"* or *"new paragraph"* while dictating |
| **Snippets** | Say a trigger phrase (e.g. *"my email"*) and the stored text is typed |
| **Pause / quit** | Right-click the tray icon |

While recording, a small floating pill at the bottom of the screen shows live
mic levels (can be turned off in Settings). Closing the dashboard window keeps
FreeFlow running in the tray.

## The dashboard

- **Home** — stats (words dictated, average WPM, minutes saved vs typing) and
  your recent dictations with copy buttons.
- **Dictionary** — teach it names and jargon: map what it *hears* to what it
  should *write* (e.g. `cube er netties → Kubernetes`, `jira → Jira`).
- **Snippets** — spoken trigger → full text expansion.
- **Settings** — hotkey, microphone, model size (tiny → medium), language
  (auto-detects 100+), auto-edit toggles, and optional AI polish.

## Optional AI polish (BYO API key)

Everything works offline. If you add an Anthropic or OpenAI API key in
**Settings → AI polish**, FreeFlow additionally:

- applies your self-corrections (*"meet at 3, actually make that 4"* → *"meet at 4"*),
- matches tone to the app you're typing in (professional in Outlook, casual in
  Slack, exact in VS Code),
- enables **command mode** (rewrite selected text by voice).

The key is stored locally in `%APPDATA%\FreeFlow\settings.json`.

## Tech notes

- Speech-to-text: [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
  (int8 on CPU), punctuation and language detection built in.
- Text is inserted via a clipboard-preserving paste, so it works in every app.
- Data lives in `%APPDATA%\FreeFlow\` (settings JSON + history SQLite). Delete
  that folder to reset.
- Run `python app.py` from the venv to see logs; `pythonw` hides the console.
- Tests: `.venv\Scripts\python -m pytest tests`

## Troubleshooting

- **Nothing types after speaking** — some elevated (admin) windows reject
  synthetic paste; run FreeFlow as administrator to dictate into those.
- **First dictation is slow** — the model loads on first use; the tray/dashboard
  status shows "Ready" when warm.
- **Win key opens the Start menu occasionally** — release Ctrl last, or switch
  the hotkey to F8/F9 in Settings.
