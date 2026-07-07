# FreeFlow

**Local-first AI voice dictation for Windows.**

Hold **Ctrl+Win** in any app, speak naturally, release — clean, formatted text appears at your cursor. FreeFlow is a privacy-focused alternative to cloud dictation tools like Wispr Flow: speech recognition runs **entirely on your own machine**. No account, no subscription, and your voice never leaves your PC.

---

## Features

### Core dictation

- **Push-to-talk** — Hold a hotkey, speak, release; text is inserted where your cursor is.
- **Hands-free mode** — Quick tap the hotkey to lock the mic; tap again to finish and insert.
- **Works everywhere** — Text is pasted via the clipboard, so it works in browsers, email, chat, IDEs, and most Windows apps.
- **Live overlay** — A floating HUD at the bottom of the screen shows a waveform and live transcript while you speak (can be disabled in Settings).
- **Spoken layout commands** — Say *"new line"*, *"new paragraph"*, *"bullet point"*, and similar phrases while dictating.
- **Filler-word cleanup** — Automatically removes *"um"*, *"uh"*, *"like, you know"*, and similar fillers.
- **100+ languages** — Auto-detect or pick a language; powered by OpenAI Whisper via [faster-whisper](https://github.com/SYSTRAN/faster-whisper).

### Personalization

- **Dictionary** — Teach FreeFlow names and jargon (e.g. map *"cube er netties"* → *"Kubernetes"*, or fix casing like *"jira"* → *"Jira"*).
- **Snippets** — Speak a trigger phrase (e.g. *"my email"*) and the stored text is typed for you.
- **Configurable hotkeys** — Change the activation key if Ctrl+Win conflicts with Windows shortcuts (e.g. F8 or F9).
- **Activation modes** — *Smart* (hold or tap), *Hold to talk* only, or *Press to toggle*.

### Dashboard

Open the dashboard from the system tray to manage everything in one place:

| Tab | What it does |
|-----|----------------|
| **Home** | Stats (words dictated, average WPM, estimated time saved vs typing) and recent dictations with copy buttons |
| **Dictionary** | Add word replacements and jargon corrections |
| **Snippets** | Create spoken trigger → text expansions |
| **Settings** | Hotkey, microphone, model size, language, overlay, and optional AI polish |

### Optional AI polish (bring your own API key)

Everything works **offline** without an API key. If you add an Anthropic or OpenAI key in **Settings → AI polish**, FreeFlow can also:

- Apply self-corrections (*"meet at 3, actually make that 4"* → *"meet at 4"*)
- Match tone to the app you're typing in (professional in Outlook, casual in Slack, exact in VS Code)
- Enable **command mode** — select text, hold **Ctrl+Win+Alt**, and speak an instruction like *"make this friendlier"* or *"turn this into bullet points"*

API keys are stored locally in `%APPDATA%\FreeFlow\settings.json`.

---

## Requirements

| Requirement | Details |
|-------------|---------|
| **Operating system** | Windows 10 or later |
| **Python** | 3.10 or newer ([python.org](https://www.python.org/downloads/)) — check **"Add Python to PATH"** during install |
| **Microphone** | Any working input device (built-in or external) |
| **Disk space** | ~500 MB for the Python environment and speech model (first dictation downloads the model, ~150 MB) |
| **Internet** | Needed only for the **first** dictation (model download) and optional AI polish |
| **Optional** | Anthropic or OpenAI API key for AI polish and command mode |

FreeFlow runs in the background from the system tray. Closing the dashboard window keeps it running.

---

## Installation

All application code lives in the [`freeflow/`](freeflow/) folder.

### Quick install (recommended)

1. **Clone or download this repository** to your computer.
2. **Install Python 3.10+** if you don't have it — during setup, enable **"Add Python to PATH"**.
3. Open the `freeflow` folder and **double-click `install.bat`**.
   - Creates a private Python virtual environment (`.venv`)
   - Installs all dependencies from `requirements.txt`
   - Adds a **FreeFlow** shortcut to your Desktop
4. **Launch FreeFlow** from the Desktop shortcut (or run `FreeFlow.bat` inside `freeflow/`).

On first launch, the speech model downloads automatically (~150 MB). Give it a minute; after that, dictation is fully offline and instant.

### Manual install

If you prefer the command line:

```bat
cd freeflow
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\pythonw.exe app.py
```

Use `pythonw.exe` to hide the console window, or `python.exe` if you want to see logs.

---

## How to use

### Basic dictation

1. Click into any text field (email, document, chat, code editor, etc.).
2. **Hold Ctrl+Win**, speak your text, then **release**.
3. Polished text appears at your cursor.

### Hands-free mode

1. **Tap Ctrl+Win** once to start recording (mic stays on).
2. Speak at your own pace.
3. **Tap Ctrl+Win** again to stop and insert the text.

### Command mode (requires API key)

1. Select text in any app.
2. **Hold Ctrl+Win+Alt**, speak an instruction (e.g. *"make this more concise"*).
3. Release — the selection is rewritten in place.

### Tray controls

Right-click the **FreeFlow** icon in the system tray to:

- Open the dashboard
- Pause dictation
- Quit the app

### Quick reference

| Action | How |
|--------|-----|
| Push-to-talk | Hold **Ctrl+Win**, speak, release |
| Hands-free | Tap **Ctrl+Win** to start; tap again to finish |
| Command mode | Select text, hold **Ctrl+Win+Alt**, speak instruction |
| Spoken commands | Say *"new line"*, *"new paragraph"*, etc. while dictating |
| Snippets | Say your trigger phrase (e.g. *"my email"*) |
| Open dashboard | Left-click tray icon, or right-click → Show |
| Pause / quit | Right-click tray icon |

---

## Settings overview

Open **Settings** in the dashboard to customize:

- **Activation mode** — Smart, Hold to talk, or Press to toggle
- **Hotkey** — Default is Ctrl+Win; change if it opens the Start menu
- **Microphone** — Pick an input device (default uses the system mic)
- **Model size** — `tiny` → `medium` (larger = more accurate, slower)
- **Language** — Auto-detect or set a specific language code
- **Overlay** — Show/hide the floating recording HUD and live transcript
- **Auto-edit** — Filler removal, spoken commands, auto-capitalize
- **AI polish** — Provider, model, and API key (optional)

---

## Where your data lives

All personal data is stored locally on your PC:

| Location | Contents |
|----------|----------|
| `%APPDATA%\FreeFlow\settings.json` | Settings, dictionary, snippets, API key |
| `%APPDATA%\FreeFlow\history.db` | Dictation history and stats |

To reset FreeFlow completely, quit the app and delete the `%APPDATA%\FreeFlow` folder.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| **Nothing types after speaking** | Some elevated (admin) windows block synthetic paste. Run FreeFlow as administrator to dictate into those apps. |
| **First dictation is slow** | The speech model loads on first use. Wait until the tray/dashboard shows **Ready**. |
| **Win key opens Start menu** | Release Ctrl last, or change the hotkey to F8/F9 in Settings. |
| **Install fails** | Confirm Python 3.10+ is installed and on your PATH (`python --version` in Command Prompt). |
| **No microphone detected** | Check Windows sound settings; pick the correct device in FreeFlow Settings. |
| **Text lost after dictation** | Every dictation is saved to history before insertion — check the Home tab in the dashboard. |

---

## Development

### Project structure

```
fable/
├── freeflow/           # Main application
│   ├── app.py          # Entry point
│   ├── install.bat     # One-click Windows installer
│   ├── FreeFlow.bat    # Launch without console
│   ├── requirements.txt
│   └── freeflow/       # Python package (audio, transcription, UI, etc.)
└── docs/               # Design and specification documents
```

### Run tests

From the `freeflow` folder with the virtual environment active:

```bat
.venv\Scripts\python -m pytest tests
```

### Tech stack

- **Speech-to-text:** [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (int8 on CPU)
- **Audio capture:** sounddevice
- **Global hotkeys:** keyboard
- **Text injection:** clipboard-preserving paste
- **Dashboard UI:** pywebview (HTML/JS)
- **System tray:** pystray
- **Optional polish:** Anthropic / OpenAI APIs

