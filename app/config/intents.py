"""Intent-level constants used by the assistant runtime."""

SUPPORTED_INTENTS = {
    "open_app",
    "close_app",
    "take_picture",
    "take_screenshot",
    "open_website",
    "search_website",
    "search_google",
    "search_youtube",
    "tell_time",
    "tell_date",
    "list_voices",
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

LLM_ALLOWED_INTENTS = (
    "open_app",
    "close_app",
    "take_picture",
    "take_screenshot",
    "open_website",
    "search_website",
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
    "exit_bot",
)

DANGEROUS_INTENTS = {
    "shutdown_computer",
    "restart_computer",
}
