# MakiBot

MakiBot is a modular local desktop assistant built with Python 3.11+.
The assistant runtime name is `Maki`.

## Features

- Rule-based local command parsing for apps, websites, search, folders, time/date, typing, help, voices, and exit.
- Optional xAI or Groq intent parsing as a safe fallback only when the rule parser returns `unknown`.
- Tool-calling-only LLM integration with no arbitrary command execution.
- Existing dangerous actions still require the current confirmation flow.
- Voice input with console fallback and optional text-to-speech.
- Persistent settings, command templates, aliases, websites, and history stored in MySQL.
- `knowledge.txt` kept locally for owner-facing guidance and startup/chat tone.

## Hybrid Intent Parsing

Maki uses a hybrid parser:

1. The existing rule-based parser runs first.
2. If it returns a known intent, that result is used unchanged.
3. If it returns `unknown`, Maki can optionally call the configured LLM provider.
4. The model is only allowed to choose from supported assistant actions through one tool schema.
5. The chosen tool call is normalized back into the existing intent format.

Important:
- the LLM only selects an intent
- it does not execute commands directly
- all execution still goes through the existing router and action modules
- shutdown and restart still go through confirmation

## LLM Provider Configuration

Use these environment variables for xAI:

```env
XAI_API_KEY=
XAI_API_URL=https://api.x.ai/v1
```

Use these environment variables for Groq:

```env
GROQ_API_KEY=
GROQ_API_URL=https://api.groq.com/openai/v1
```

Compatibility aliases:
- `GROK_API_KEY`
- `GROK_API_URL`

Provider behavior:
- if an xAI key is present, Maki uses xAI
- if a Groq or Grok key is present and no xAI key is set, Maki uses Groq
- you can override this with `llm_provider` in settings: `auto`, `xai`, or `groq`

Runtime settings stored in MySQL:
- `llm_parser_enabled`
- `llm_provider`
- `llm_model`
- `llm_timeout_seconds`
- speech, wake-word, TTS, and conversation settings

Defaults:
- xAI model: `grok-4.20-reasoning`
- fast swap option: `grok-3-mini-fast`
- Groq model: `openai/gpt-oss-20b`
- timeout: `15` seconds

## MySQL Storage

MySQL is the required source of truth for:
- assistant settings
- command templates
- website aliases
- app aliases
- folder aliases
- command history

Environment variables:

```env
MAKI_DB_ENABLED=true
MAKI_DB_HOST=127.0.0.1
MAKI_DB_PORT=3306
MAKI_DB_USER=root
MAKI_DB_PASSWORD=your_password
MAKI_DB_NAME=maki_assistant
```

Tables created on first startup:
- `assistant_settings`
- `command_patterns`
- `website_aliases`
- `app_aliases`
- `folder_aliases`
- `command_history`

Website aliases support both open links and optional search templates.
Useful columns in `website_aliases`:
- `alias`
- `display_name`
- `url`
- `search_url_template`

Examples:
- opening: `open youtube`
- dynamic search: `search github for makibot`
- short search: `wikipedia python`

If MySQL is unavailable or disabled, startup stops with an error. Maki no longer falls back to `app/data/*.json` for runtime state.

## knowledge.txt

`knowledge.txt` remains the only local content file used at runtime.
It is used for:
- startup greeting customization
- preferred owner title
- conversational grounding for chat-style replies

## Speech Flow

Maki uses a turn-based speech loop:
1. It tries to capture one spoken command.
2. If speech recognition is unavailable or unclear, it falls back to typed console input.
3. Every assistant response is printed to the console.
4. If speech output is enabled and a TTS backend is available, the response is also spoken aloud.

## Install

```bash
pip install -r requirements.txt
```

Main dependencies:
- `SpeechRecognition`
- `pywebview`
- `PyAudio`
- `pyttsx3`
- `mysql-connector-python`
- `openai`

## Run

```bash
python run.py
```

## Desktop UI

The first desktop UI scaffold uses `pywebview` with a local HTML, CSS, and JavaScript frontend.

Run it with:

```bash
python run_ui.py
```

Current UI scaffold behavior:
- dark futuristic desktop shell with an animated central orb
- typed command input with placeholder Python bridge responses
- microphone button with placeholder listening state
- session-only recent activity panel

Notes:
- this UI is additive and does not replace the console runtime yet
- Bootstrap 5 is loaded from CDN in v1, so the styled UI expects internet access for that asset
- the Python bridge is intentionally shallow for now and does not invoke the live assistant loop

## Tests

```bash
python -m unittest
```
