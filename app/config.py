"""Configuration constants and default values for the MakiBot backend."""

from pathlib import Path

from app.speech.wake_word import DEFAULT_WAKE_PHRASES

BOT_NAME = "Maki"

APP_DIR = Path(__file__).resolve().parent
BASE_DIR = APP_DIR.parent
DATA_DIR = APP_DIR / "data"
HOME_DIR = Path.home()

APPS_FILE = DATA_DIR / "apps.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
HISTORY_FILE = DATA_DIR / "history.json"

VOICE_TIMEOUT_SECONDS = 5
VOICE_PHRASE_LIMIT_SECONDS = 8
MIN_VOICE_TIMEOUT_SECONDS = 1
MAX_VOICE_TIMEOUT_SECONDS = 30
MIN_VOICE_PHRASE_LIMIT_SECONDS = 1
MAX_VOICE_PHRASE_LIMIT_SECONDS = 30

DEFAULT_HISTORY_LIMIT = 100
MAX_HISTORY_LIMIT = 1000

SUPPORTED_INTENTS = {
    "open_app",
    "open_website",
    "search_google",
    "search_youtube",
    "tell_time",
    "tell_date",
    "create_folder",
    "open_folder",
    "type_text",
    "shutdown_computer",
    "restart_computer",
    "list_commands",
    "help",
    "confirm_yes",
    "confirm_no",
    "exit_bot",
    "unknown",
}

DANGEROUS_INTENTS = {
    "shutdown_computer",
    "restart_computer",
}

DEFAULT_SETTINGS: dict[str, object] = {
    "bot_name": BOT_NAME,
    "speech_input_enabled": True,
    "speech_output_enabled": True,
    "microphone_index": None,
    "voice_timeout_seconds": VOICE_TIMEOUT_SECONDS,
    "voice_phrase_limit_seconds": VOICE_PHRASE_LIMIT_SECONDS,
    "wake_word_enabled": False,
    "wake_phrases": list(DEFAULT_WAKE_PHRASES),
    "require_confirmation": True,
    "console_fallback_enabled": True,
    "typing_live_mode": False,
    "history_limit": DEFAULT_HISTORY_LIMIT,
    "allow_system_commands": False,
    "open_browser_enabled": True,
}

WEBSITE_ALIASES: dict[str, str] = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "gmail": "https://mail.google.com",
    "github": "https://github.com",
    "wikipedia": "https://www.wikipedia.org",
}

BUILTIN_APP_ENTRIES: list[dict[str, object]] = [
    {"name": "calculator", "aliases": ["calculator", "calc"], "command": ["calc"]},
    {"name": "notepad", "aliases": ["notepad"], "command": ["notepad"]},
    {"name": "paint", "aliases": ["paint"], "command": ["mspaint"]},
    {"name": "powershell", "aliases": ["powershell"], "command": ["powershell"]},
    {"name": "command prompt", "aliases": ["command prompt", "cmd"], "command": ["cmd"]},
    {"name": "file explorer", "aliases": ["file explorer", "explorer"], "command": ["explorer"]},
    {"name": "chrome", "aliases": ["chrome", "google chrome"], "command": ["chrome"]},
    {"name": "edge", "aliases": ["edge", "microsoft edge"], "command": ["msedge"]},
    {"name": "vscode", "aliases": ["vscode", "visual studio code", "code"], "command": ["code"]},
]

BUILTIN_FOLDER_ENTRIES: list[dict[str, object]] = [
    {"name": "desktop", "aliases": ["desktop"], "path": HOME_DIR / "Desktop"},
    {"name": "documents", "aliases": ["documents", "document"], "path": HOME_DIR / "Documents"},
    {"name": "downloads", "aliases": ["downloads", "download"], "path": HOME_DIR / "Downloads"},
    {"name": "pictures", "aliases": ["pictures", "picture"], "path": HOME_DIR / "Pictures"},
]

COMMAND_HELP: dict[str, str] = {
    "open_app": "Open a known desktop application, for example 'open notepad'.",
    "open_website": "Open a website alias or URL, for example 'go to youtube'.",
    "search_google": "Search Google, for example 'google python decorators'.",
    "search_youtube": "Search YouTube, for example 'youtube jazz piano'.",
    "tell_time": "Tell the current local time.",
    "tell_date": "Tell today's local date.",
    "create_folder": "Create a folder inside the project workspace.",
    "open_folder": "Open a known folder such as Downloads or a workspace folder.",
    "type_text": "Preview typed text, or type for real when enabled in settings.",
    "shutdown_computer": "Request a computer shutdown after confirmation.",
    "restart_computer": "Request a computer restart after confirmation.",
    "list_commands": "List the commands the assistant currently supports.",
    "help": "Show a short help summary.",
    "exit_bot": "Exit the assistant loop.",
}


# TODO: Move more user-editable values into settings or environment variables.
