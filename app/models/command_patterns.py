"""MySQL-backed model helpers for command templates."""

from typing import Any

from app.services.database import _fetch_rows, ensure_database_ready

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
    {"phrase_template": "list voices", "intent": "list_voices", "fixed_target": "", "priority": 55},
    {"phrase_template": "show voices", "intent": "list_voices", "fixed_target": "", "priority": 56},
    {"phrase_template": "available voices", "intent": "list_voices", "fixed_target": "", "priority": 57},
    {"phrase_template": "what voices do you have", "intent": "list_voices", "fixed_target": "", "priority": 58},
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
    {"phrase_template": "search {site} for {target}", "intent": "search_website", "fixed_target": "", "priority": 115},
    {"phrase_template": "search on {site} for {target}", "intent": "search_website", "fixed_target": "", "priority": 116},
    {"phrase_template": "{site} {target}", "intent": "search_website", "fixed_target": "", "priority": 117},
    {"phrase_template": "make me a folder called {target}", "intent": "create_folder", "fixed_target": "", "priority": 120},
    {"phrase_template": "make a folder called {target}", "intent": "create_folder", "fixed_target": "", "priority": 121},
    {"phrase_template": "create me a folder called {target}", "intent": "create_folder", "fixed_target": "", "priority": 122},
    {"phrase_template": "create a folder called {target}", "intent": "create_folder", "fixed_target": "", "priority": 123},
    {"phrase_template": "new folder {target}", "intent": "create_folder", "fixed_target": "", "priority": 124},
    {"phrase_template": "open folder {target}", "intent": "open_folder", "fixed_target": "", "priority": 130},
    {"phrase_template": "go to folder {target}", "intent": "open_folder", "fixed_target": "", "priority": 131},
    {"phrase_template": "type {target}", "intent": "type_text", "fixed_target": "", "priority": 140},
    {"phrase_template": "write {target}", "intent": "type_text", "fixed_target": "", "priority": 141},
    {"phrase_template": "take a picture", "intent": "take_picture", "fixed_target": "", "priority": 142},
    {"phrase_template": "take picture", "intent": "take_picture", "fixed_target": "", "priority": 143},
    {"phrase_template": "take a photo", "intent": "take_picture", "fixed_target": "", "priority": 144},
    {"phrase_template": "take photo", "intent": "take_picture", "fixed_target": "", "priority": 145},
    {"phrase_template": "capture a picture", "intent": "take_picture", "fixed_target": "", "priority": 146},
    {"phrase_template": "capture a photo", "intent": "take_picture", "fixed_target": "", "priority": 147},
    {"phrase_template": "open camera and take a picture", "intent": "take_picture", "fixed_target": "", "priority": 148},
    {"phrase_template": "open the camera and take a picture", "intent": "take_picture", "fixed_target": "", "priority": 149},
    {"phrase_template": "take a screenshot", "intent": "take_screenshot", "fixed_target": "", "priority": 150},
    {"phrase_template": "take screenshot", "intent": "take_screenshot", "fixed_target": "", "priority": 151},
    {"phrase_template": "capture a screenshot", "intent": "take_screenshot", "fixed_target": "", "priority": 152},
    {"phrase_template": "capture the screen", "intent": "take_screenshot", "fixed_target": "", "priority": 153},
    {"phrase_template": "screenshot", "intent": "take_screenshot", "fixed_target": "", "priority": 154},
    {"phrase_template": "take a screen shot", "intent": "take_screenshot", "fixed_target": "", "priority": 155},
    {"phrase_template": "close app {target}", "intent": "close_app", "fixed_target": "", "priority": 160},
    {"phrase_template": "close the app {target}", "intent": "close_app", "fixed_target": "", "priority": 161},
    {"phrase_template": "close {target}", "intent": "close_app", "fixed_target": "", "priority": 162},
    {"phrase_template": "close program {target}", "intent": "close_app", "fixed_target": "", "priority": 163},
    {"phrase_template": "open website {target}", "intent": "open_target", "fixed_target": "", "priority": 170},
    {"phrase_template": "visit {target}", "intent": "open_target", "fixed_target": "", "priority": 171},
    {"phrase_template": "go to {target}", "intent": "open_target", "fixed_target": "", "priority": 172},
    {"phrase_template": "open {target}", "intent": "open_target", "fixed_target": "", "priority": 180},
    {"phrase_template": "launch {target}", "intent": "open_target", "fixed_target": "", "priority": 181},
    {"phrase_template": "start {target}", "intent": "open_target", "fixed_target": "", "priority": 182},
]


def load_command_patterns() -> list[dict[str, Any]]:
    """Load enabled command templates from the MySQL command pattern table."""
    ensure_database_ready()
    rows = _fetch_rows(
        """
        SELECT phrase_template, intent, fixed_target, priority
        FROM command_patterns
        WHERE enabled = 1
        ORDER BY priority ASC, CHAR_LENGTH(phrase_template) DESC
        """
    )
    patterns: list[dict[str, Any]] = []
    for row in rows:
        template = str(row.get("phrase_template", "")).strip()
        intent = str(row.get("intent", "")).strip()
        if not template or not intent:
            continue

        patterns.append(
            {
                "phrase_template": template,
                "intent": intent,
                "fixed_target": str(row.get("fixed_target") or "").strip(),
                "priority": int(row.get("priority") or 100),
            }
        )
    return patterns


def seed_default_command_patterns(connection: Any) -> None:
    """Insert any missing default command templates into the database."""
    cursor = connection.cursor()
    for pattern in DEFAULT_COMMAND_PATTERNS:
        cursor.execute(
            """
            INSERT IGNORE INTO command_patterns (phrase_template, intent, fixed_target, priority, enabled)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                str(pattern.get("phrase_template", "")),
                str(pattern.get("intent", "")),
                str(pattern.get("fixed_target", "")),
                int(pattern.get("priority", 100)),
                True,
            ),
        )
