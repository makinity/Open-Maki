"""Service helpers for reading and writing assistant settings."""

import json
from pathlib import Path
from typing import Any

from app.config import (
    DEFAULT_HISTORY_LIMIT,
    DEFAULT_SETTINGS,
    MAX_HISTORY_LIMIT,
    MAX_VOICE_PHRASE_LIMIT_SECONDS,
    MAX_VOICE_TIMEOUT_SECONDS,
    MIN_VOICE_PHRASE_LIMIT_SECONDS,
    MIN_VOICE_TIMEOUT_SECONDS,
    SETTINGS_FILE,
)
from app.services.database import (
    database_is_ready,
    load_settings_dict,
    save_settings_dict,
)
from app.utils.helpers import normalize_text

_BOOLEAN_SETTING_KEYS = {
    "wake_word_enabled",
    "require_confirmation",
    "console_fallback_enabled",
    "typing_live_mode",
    "allow_system_commands",
    "open_browser_enabled",
}


def load_settings() -> dict[str, Any]:
    """Load settings from disk and return validated values."""
    if database_is_ready():
        data = load_settings_dict()
        settings = validate_settings(data if isinstance(data, dict) else {})

        if data != settings:
            save_settings(settings)

        return settings

    data = _read_json_file(SETTINGS_FILE)
    settings = validate_settings(data if isinstance(data, dict) else {})

    if data != settings:
        save_settings(settings)

    return settings


def save_settings(settings: dict[str, Any]) -> dict[str, Any]:
    """Validate and save settings to disk."""
    validated_settings = validate_settings(settings)

    if database_is_ready():
        save_settings_dict(validated_settings)
        return validated_settings

    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with SETTINGS_FILE.open("w", encoding="utf-8") as file:
        json.dump(validated_settings, file, indent=2)

    return validated_settings


def update_settings(updates: dict[str, Any]) -> dict[str, Any]:
    """Apply updates on top of the current settings and persist them."""
    current_settings = load_settings()
    current_settings.update(updates)
    return save_settings(current_settings)


def validate_settings(settings: dict[str, Any]) -> dict[str, Any]:
    """Return a cleaned settings dictionary with safe default values."""
    cleaned_settings = _copy_default_settings()
    for key, value in settings.items():
        if isinstance(key, str) and key != "voice_enabled":
            cleaned_settings[key] = value

    bot_name = normalize_text(str(settings.get("bot_name", DEFAULT_SETTINGS["bot_name"])))
    cleaned_settings["bot_name"] = bot_name or str(DEFAULT_SETTINGS["bot_name"])

    legacy_voice_enabled = _coerce_bool(settings.get("voice_enabled", True))
    cleaned_settings["speech_input_enabled"] = _coerce_bool(
        settings.get("speech_input_enabled", legacy_voice_enabled)
    )
    cleaned_settings["speech_output_enabled"] = _coerce_bool(
        settings.get("speech_output_enabled", legacy_voice_enabled)
    )

    for key in _BOOLEAN_SETTING_KEYS:
        cleaned_settings[key] = _coerce_bool(settings.get(key, DEFAULT_SETTINGS[key]))

    cleaned_settings["wake_phrases"] = _coerce_string_list(
        settings.get("wake_phrases", DEFAULT_SETTINGS["wake_phrases"]),
        default=[str(item) for item in DEFAULT_SETTINGS["wake_phrases"]],
    )
    cleaned_settings["voice_timeout_seconds"] = _coerce_int(
        settings.get("voice_timeout_seconds", DEFAULT_SETTINGS["voice_timeout_seconds"]),
        default=int(DEFAULT_SETTINGS["voice_timeout_seconds"]),
        minimum=MIN_VOICE_TIMEOUT_SECONDS,
        maximum=MAX_VOICE_TIMEOUT_SECONDS,
    )
    cleaned_settings["microphone_index"] = _coerce_optional_int(
        settings.get("microphone_index", DEFAULT_SETTINGS["microphone_index"])
    )
    cleaned_settings["voice_phrase_limit_seconds"] = _coerce_int(
        settings.get(
            "voice_phrase_limit_seconds",
            DEFAULT_SETTINGS["voice_phrase_limit_seconds"],
        ),
        default=int(DEFAULT_SETTINGS["voice_phrase_limit_seconds"]),
        minimum=MIN_VOICE_PHRASE_LIMIT_SECONDS,
        maximum=MAX_VOICE_PHRASE_LIMIT_SECONDS,
    )
    cleaned_settings["history_limit"] = _coerce_int(
        settings.get("history_limit", DEFAULT_HISTORY_LIMIT),
        default=DEFAULT_HISTORY_LIMIT,
        minimum=0,
        maximum=MAX_HISTORY_LIMIT,
    )
    cleaned_settings.pop("voice_enabled", None)

    return cleaned_settings


def _copy_default_settings() -> dict[str, Any]:
    """Return a copy of the default settings without sharing mutable values."""
    copied_settings: dict[str, Any] = {}
    for key, value in DEFAULT_SETTINGS.items():
        if isinstance(value, list):
            copied_settings[key] = list(value)
        elif isinstance(value, dict):
            copied_settings[key] = dict(value)
        else:
            copied_settings[key] = value

    return copied_settings


def _coerce_bool(value: Any) -> bool:
    """Convert common truthy and falsy values into a boolean."""
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False

    return bool(value)


def _coerce_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    """Convert a value into a bounded integer using a safe fallback."""
    try:
        parsed_value = int(value)
    except (TypeError, ValueError):
        return default

    return max(minimum, min(maximum, parsed_value))


def _coerce_string_list(value: Any, default: list[str]) -> list[str]:
    """Convert a value into a cleaned list of non-empty strings."""
    if isinstance(value, list):
        cleaned_values: list[str] = []
        for item in value:
            cleaned_item = normalize_text(str(item))
            if cleaned_item and cleaned_item not in cleaned_values:
                cleaned_values.append(cleaned_item)
        if cleaned_values:
            return cleaned_values

    if isinstance(value, str):
        cleaned_value = normalize_text(value)
        if cleaned_value:
            return [cleaned_value]

    return list(default)


def _coerce_optional_int(value: Any) -> int | None:
    """Convert a value into an integer or return None when it is unset."""
    if value is None:
        return None

    if isinstance(value, str) and not value.strip():
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _read_json_file(path: Path) -> Any:
    """Read JSON from disk and return None when the file is invalid."""
    try:
        with path.open("r", encoding="utf-8-sig") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


# TODO: Add support for named assistant profiles when multi-user setups are needed.
