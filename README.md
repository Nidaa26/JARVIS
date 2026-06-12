# JARVIS- 

A cross-platform (macOS / Windows / Linux) AI assistant for group projects.
It manages **tasks, notes, and reminders entirely locally** (instant, free,
offline) and sends everything else to **Claude** for streamed, conversational
answers — by voice or by keyboard.

## Features

- 💬 **Chat with Claude** — streamed responses with rolling conversation memory
- ✅ **Tasks** — `task add / list / done / remove`, shared JSON storage
- 📝 **Notes** — quick project notes
- ⏰ **Reminders** — `remind 45m submit draft`; fire from a background thread
  and survive restarts (missed ones are announced on launch)
- 🎤 **Voice mode (optional)** — speech-to-text + text-to-speech with clean
  per-platform backends and automatic fallback to text mode
- 🔒 **No secrets in code** — all configuration via environment / `.env`

## Quick start

### macOS / Linux

```bash
./scripts/setup.sh            # text mode only
./scripts/setup.sh --voice    # with voice extras
# edit .env and add your ANTHROPIC_API_KEY
./scripts/run.sh              # or: ./scripts/run.sh --voice
```

### Windows (PowerShell)

```powershell
.\scripts\setup.ps1           # text mode only
.\scripts\setup.ps1 -Voice    # with voice extras
# edit .env and add your ANTHROPIC_API_KEY
.\scripts\run.ps1             # or: .\scripts\run.ps1 -Voice
```

> If PowerShell blocks the scripts, run once:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### Manual (any platform)

```bash
python -m venv .venv && source .venv/bin/activate   # .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env                                 # then add your API key
python -m assistant            # add --voice for voice mode
```

## Usage

```
You: task add finish the literature review
Assistant: Added task 1: finish the literature review
You: remind 30m check on the survey responses
Assistant: Okay — I'll remind you at 15:42: check on the survey responses
You: how should we split a 20-page report between 4 people?
Assistant: A clean split is by section ownership rather than page count…
```

Type `help` for the full command list. Anything that isn't a command goes to
the AI.

## Configuration

Everything is configurable via environment variables (see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | **Required.** Your Claude API key |
| `ASSISTANT_MODEL` | `claude-opus-4-8` | Claude model to use |
| `ASSISTANT_EFFORT` | `low` | Response effort: `low` = fastest, `high`/`max` = deepest |
| `ASSISTANT_MAX_TOKENS` | `8000` | Max response length |
| `ASSISTANT_HISTORY_LIMIT` | `20` | Messages of context per request (speed/cost lever) |
| `ASSISTANT_VOICE` | `0` | Enable voice mode by default |
| `ASSISTANT_DATA_DIR` | `~/.group-project-assistant` | Where tasks/notes/logs live |
| `LOG_LEVEL` | `INFO` | File log verbosity |

## Voice support

| Platform | Text-to-speech | Speech-to-text |
|---|---|---|
| macOS | built-in `say` (no extra installs) | SpeechRecognition + PyAudio (`brew install portaudio` first) |
| Windows | pyttsx3 (SAPI5), falls back to built-in PowerShell SAPI | SpeechRecognition + PyAudio |
| Linux | pyttsx3 (espeak) | SpeechRecognition + PyAudio (`apt install portaudio19-dev`) |

If any voice component is missing, the assistant degrades gracefully to
text — it never crashes for lack of audio hardware.

## Architecture

```
assistant/
├── __main__.py        CLI entry point (argument parsing only)
├── app.py             Wiring + main interaction loop
├── config.py          All settings, env-driven (no hardcoded values)
├── commands.py        Local command registry — zero API calls
├── llm.py             Claude client: streaming, history, caching, errors
├── storage.py         Thread-safe atomic JSON stores
├── scheduler.py       Background reminder thread (condition-variable based)
├── logging_setup.py   Console + rotating file logging
└── speech/
    ├── tts.py         TTS backends: macOS say / pyttsx3 / PowerShell SAPI
    └── stt.py         Optional SpeechRecognition wrapper
```

Design choices for speed and cost:

- **Local-first commands**: tasks/notes/reminders never touch the API.
- **Streaming**: first words appear immediately instead of waiting for the
  full response.
- **Prompt caching**: the system prompt is marked cacheable.
- **History trimming**: only the last `ASSISTANT_HISTORY_LIMIT` messages are
  sent, bounding both latency and cost.
- **Lazy imports**: the Anthropic SDK and voice libraries load only when
  first used, keeping startup near-instant.
- **Event-driven scheduler**: the reminder thread sleeps on a condition
  variable — no polling loop burning CPU.

## Running tests

```bash
pip install pytest
pytest
```

The test suite covers storage (including corrupt-file recovery and
atomic writes), command parsing/dispatch, and the reminder scheduler —
no API key needed.

## License

MIT
