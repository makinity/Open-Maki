"""Configuration constants and default values for the Maki backend."""

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

DEFAULT_WEBSITE_ENTRIES: list[dict[str, str]] = [
    {"alias": "youtube", "name": "YouTube", "url": "https://www.youtube.com"},
    {"alias": "gmail", "name": "Gmail", "url": "https://mail.google.com"},
    {"alias": "google", "name": "Google", "url": "https://www.google.com"},
    {"alias": "facebook", "name": "Facebook", "url": "https://www.facebook.com"},
    {"alias": "github", "name": "GitHub", "url": "https://github.com"},
    {"alias": "wikipedia", "name": "Wikipedia", "url": "https://www.wikipedia.org"},
]

WEBSITE_ALIASES: dict[str, str] = {
    entry["alias"]: entry["url"] for entry in DEFAULT_WEBSITE_ENTRIES
}

DEFAULT_COMMAND_PATTERNS: list[dict[str, object]] = [
    {"phrase_template": "yes", "intent": "confirm_yes", "fixed_target": "", "priority": 10},
    {"phrase_template": "yes please", "intent": "confirm_yes", "fixed_target": "", "priority": 11},
    {"phrase_template": "confirm", "intent": "confirm_yes", "fixed_target": "", "priority": 12},
    {"phrase_template": "confirm it", "intent": "confirm_yes", "fixed_target": "", "priority": 13},
    {"phrase_template": "do it", "intent": "confirm_yes", "fixed_target": "", "priority": 14},
    {"phrase_template": "no", "intent": "confirm_no", "fixed_target": "", "priority": 20},
    {"phrase_template": "no thanks", "intent": "confirm_no", "fixed_target": "", "priority": 21},
    {"phrase_template": "cancel", "intent": "confirm_no", "fixed_target": "", "priority": 22},
    {"phrase_template": "never mind", "intent": "confirm_no", "fixed_target": "", "priority": 23},
    {"phrase_template": "stop that", "intent": "confirm_no", "fixed_target": "", "priority": 24},
    {"phrase_template": "exit", "intent": "exit_bot", "fixed_target": "", "priority": 30},
    {"phrase_template": "exit bot", "intent": "exit_bot", "fixed_target": "", "priority": 31},
    {"phrase_template": "quit", "intent": "exit_bot", "fixed_target": "", "priority": 32},
    {"phrase_template": "quit bot", "intent": "exit_bot", "fixed_target": "", "priority": 33},
    {"phrase_template": "goodbye", "intent": "exit_bot", "fixed_target": "", "priority": 34},
    {"phrase_template": "bye", "intent": "exit_bot", "fixed_target": "", "priority": 35},
    {"phrase_template": "time", "intent": "tell_time", "fixed_target": "", "priority": 40},
    {"phrase_template": "current time", "intent": "tell_time", "fixed_target": "", "priority": 41},
    {"phrase_template": "what time is it", "intent": "tell_time", "fixed_target": "", "priority": 42},
    {"phrase_template": "tell me the time", "intent": "tell_time", "fixed_target": "", "priority": 43},
    {"phrase_template": "date", "intent": "tell_date", "fixed_target": "", "priority": 50},
    {"phrase_template": "today's date", "intent": "tell_date", "fixed_target": "", "priority": 51},
    {"phrase_template": "what date is it", "intent": "tell_date", "fixed_target": "", "priority": 52},
    {"phrase_template": "what is today's date", "intent": "tell_date", "fixed_target": "", "priority": 53},
    {"phrase_template": "tell me the date", "intent": "tell_date", "fixed_target": "", "priority": 54},
    {"phrase_template": "help", "intent": "help", "fixed_target": "", "priority": 60},
    {"phrase_template": "what can you do", "intent": "help", "fixed_target": "", "priority": 61},
    {"phrase_template": "what do you do", "intent": "help", "fixed_target": "", "priority": 62},
    {"phrase_template": "how can you help", "intent": "help", "fixed_target": "", "priority": 63},
    {"phrase_template": "list commands", "intent": "list_commands", "fixed_target": "", "priority": 70},
    {"phrase_template": "show commands", "intent": "list_commands", "fixed_target": "", "priority": 71},
    {"phrase_template": "show me the commands", "intent": "list_commands", "fixed_target": "", "priority": 72},
    {"phrase_template": "what commands do you know", "intent": "list_commands", "fixed_target": "", "priority": 73},
    {"phrase_template": "shutdown computer", "intent": "shutdown_computer", "fixed_target": "computer", "priority": 80},
    {"phrase_template": "shut down computer", "intent": "shutdown_computer", "fixed_target": "computer", "priority": 81},
    {"phrase_template": "turn off computer", "intent": "shutdown_computer", "fixed_target": "computer", "priority": 82},
    {"phrase_template": "restart computer", "intent": "restart_computer", "fixed_target": "computer", "priority": 90},
    {"phrase_template": "reboot computer", "intent": "restart_computer", "fixed_target": "computer", "priority": 91},
    {"phrase_template": "search youtube for {target}", "intent": "search_youtube", "fixed_target": "", "priority": 100},
    {"phrase_template": "search on youtube for {target}", "intent": "search_youtube", "fixed_target": "", "priority": 101},
    {"phrase_template": "youtube {target}", "intent": "search_youtube", "fixed_target": "", "priority": 102},
    {"phrase_template": "search google for {target}", "intent": "search_google", "fixed_target": "", "priority": 110},
    {"phrase_template": "google {target}", "intent": "search_google", "fixed_target": "", "priority": 111},
    {"phrase_template": "search for {target}", "intent": "search_google", "fixed_target": "", "priority": 112},
    {"phrase_template": "make me a folder called {target}", "intent": "create_folder", "fixed_target": "", "priority": 120},
    {"phrase_template": "make a folder called {target}", "intent": "create_folder", "fixed_target": "", "priority": 121},
    {"phrase_template": "create me a folder called {target}", "intent": "create_folder", "fixed_target": "", "priority": 122},
    {"phrase_template": "create a folder called {target}", "intent": "create_folder", "fixed_target": "", "priority": 123},
    {"phrase_template": "new folder {target}", "intent": "create_folder", "fixed_target": "", "priority": 124},
    {"phrase_template": "open folder {target}", "intent": "open_folder", "fixed_target": "", "priority": 130},
    {"phrase_template": "go to folder {target}", "intent": "open_folder", "fixed_target": "", "priority": 131},
    {"phrase_template": "type {target}", "intent": "type_text", "fixed_target": "", "priority": 140},
    {"phrase_template": "write {target}", "intent": "type_text", "fixed_target": "", "priority": 141},
    {"phrase_template": "open website {target}", "intent": "open_target", "fixed_target": "", "priority": 150},
    {"phrase_template": "visit {target}", "intent": "open_target", "fixed_target": "", "priority": 151},
    {"phrase_template": "go to {target}", "intent": "open_target", "fixed_target": "", "priority": 152},
    {"phrase_template": "open {target}", "intent": "open_target", "fixed_target": "", "priority": 160},
    {"phrase_template": "launch {target}", "intent": "open_target", "fixed_target": "", "priority": 161},
    {"phrase_template": "start {target}", "intent": "open_target", "fixed_target": "", "priority": 162},
]

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


# TODO: Move more user-editable values into database-backed admin workflows.
