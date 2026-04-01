# MakiBot

MakiBot is a modular local desktop assistant built with Python 3.11+.

Phase 4 adds a cleaner speech layer on top of the existing command system:
- turn-based voice input with immediate console fallback
- console-first responses with optional text-to-speech
- rule-based local command handling with no cloud AI features
- safer system actions with confirmation flow and settings validation
- persistent history records that track whether input came from voice, console, or the system

## Features

- Voice input through `SpeechRecognition` when a microphone is available.
- Reliable typed input fallback when voice input is disabled, unavailable, or times out.
- Console output for every response, with optional spoken output through `pyttsx3`.
- Rule-based commands for apps, websites, web search, time/date, folders, typing, help, and exit.
- Pending confirmation support for dangerous commands such as shutdown and restart.
- Persistent settings, command templates, app aliases, website aliases, and command history stored in MySQL when enabled.
- Local JSON fallback remains available when MySQL is not configured yet.

## Supported Commands

Examples:
- `open chrome`
- `launch notepad`
- `open youtube`
- `open gmail`
- `open google`
- `open facebook`
- `go to youtube`
- `google python decorators`
- `search google for python speech recognition`
- `youtube jazz piano`
- `search youtube for lofi`
- `what time is it`
- `what is today's date`
- `create folder projects`
- `open folder downloads`
- `type hello world`
- `shutdown computer`
- `restart computer`
- `help`
- `list commands`
- `yes`
- `no`
- `exit`

## Speech Flow

MakiBot uses a simple turn-based speech loop:
1. It tries to capture one spoken command from the microphone.
2. If speech recognition is unavailable, the microphone is missing, or no speech is recognized in time, it falls back to typed console input.
3. Every assistant response is printed to the console.
4. If `pyttsx3` is available and speech output is enabled, the same response is also spoken aloud.

This keeps the assistant usable even when optional audio packages are missing.

## Optional Speech Dependencies

Install the project dependencies first:

```bash
pip install -r requirements.txt
```

Speech features depend on these packages:
- `SpeechRecognition`
- `PyAudio`
- `pyttsx3`

If one of them is unavailable, MakiBot should still run locally with console fallback behavior.

## MySQL Storage

Maki can now use MySQL as the source of truth for:
- assistant settings such as wake phrases and speech toggles
- command templates such as `open {target}` or `search youtube for {target}`
- website aliases
- app and folder aliases
- command history

Enable it with environment variables:

```env
MAKI_DB_ENABLED=true
MAKI_DB_HOST=127.0.0.1
MAKI_DB_PORT=3306
MAKI_DB_USER=root
MAKI_DB_PASSWORD=your_password
MAKI_DB_NAME=maki_assistant
```

On first startup, Maki creates and seeds these tables:
- `assistant_settings`
- `command_patterns`
- `website_aliases`
- `app_aliases`
- `folder_aliases`
- `command_history`

Important:
- when MySQL is enabled, those tables become the main source of truth
- existing `apps.json` aliases are imported into MySQL the first time the tables are seeded
- if MySQL is unavailable, Maki falls back to the local JSON files

## apps.json Aliases

`app/data/apps.json` can define custom app and folder aliases.

Example:

```json
{
  "chrome": {
    "type": "app",
    "command": ["chrome"],
    "aliases": ["google chrome", "browser"]
  },
  "work": {
    "type": "folder",
    "path": "C:\\Users\\YourName\\Documents\\Work",
    "aliases": ["work folder", "office files"]
  }
}
```

Notes:
- String values still work as simple app commands.
- Folder entries use `type: "folder"` and a `path`.
- Built-in aliases exist for common apps and folders, but custom aliases are more reliable.

## Settings

`app/data/settings.json` supports these keys when JSON fallback mode is active:
- `bot_name`
- `speech_input_enabled`
- `speech_output_enabled`
- `voice_timeout_seconds`
- `voice_phrase_limit_seconds`
- `require_confirmation`
- `console_fallback_enabled`
- `typing_live_mode`
- `history_limit`
- `allow_system_commands`
- `open_browser_enabled`

Compatibility note:
- legacy `voice_enabled` is still understood during settings validation, but MakiBot now saves the split `speech_input_enabled` and `speech_output_enabled` settings instead.

Safety note:
- `allow_system_commands` should stay `false` unless you explicitly want confirmed shutdown and restart commands to execute.

## Running

```bash
python run.py
```

## Tests

```bash
python -m unittest
```
