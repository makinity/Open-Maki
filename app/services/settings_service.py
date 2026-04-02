"""Service helpers for reading and writing assistant settings."""

from typing import Any

from app.config import (
    DEFAULT_HISTORY_LIMIT,
    DEFAULT_LLM_TIMEOUT_SECONDS,
    DEFAULT_SETTINGS,
    MAX_HISTORY_LIMIT,
    MAX_LLM_TIMEOUT_SECONDS,
    MAX_VOICE_PHRASE_LIMIT_SECONDS,
    MAX_VOICE_TIMEOUT_SECONDS,
    MIN_LLM_TIMEOUT_SECONDS,
    MIN_VOICE_PHRASE_LIMIT_SECONDS,
    MIN_VOICE_TIMEOUT_SECONDS,
    get_default_llm_model,
    get_llm_api_key,
    normalize_llm_model,
)
from app.services.database import (
    ensure_database_ready,
    load_settings_dict,
    save_settings_dict,
)
from app.utils.helpers import normalize_text

_BOOLEAN_SETTING_KEYS = {
    "wake_word_enabled",
    "require_confirmation",
    "console_fallback_enabled",
    "conversation_mode_enabled",
    "always_voice_responses",
    "typing_live_mode",
    "allow_system_commands",
    "open_browser_enabled",
}


def load_settings() -> dict[str, Any]:
    """Load settings from MySQL and return validated values."""
    ensure_database_ready()
    data = load_settings_dict()
    settings = validate_settings(data if isinstance(data, dict) else {})

    if data != settings:
        save_settings_dict(settings)

    return settings


def save_settings(settings: dict[str, Any]) -> dict[str, Any]:
    """Validate and save settings into MySQL."""
    ensure_database_ready()
    validated_settings = validate_settings(settings)
    save_settings_dict(validated_settings)
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
    cleaned_settings["llm_provider"] = _coerce_llm_provider(
        settings.get("llm_provider", DEFAULT_SETTINGS["llm_provider"])
    )
    cleaned_settings["llm_parser_enabled"] = _coerce_optional_bool(
        settings.get("llm_parser_enabled")
    )
    if cleaned_settings["llm_parser_enabled"] is None:
        cleaned_settings["llm_parser_enabled"] = bool(
            get_llm_api_key(cleaned_settings["llm_provider"])
        )
    cleaned_settings["llm_model"] = normalize_llm_model(
        _coerce_string(
            settings.get(
                "llm_model",
                get_default_llm_model(cleaned_settings["llm_provider"]),
            ),
            default=get_default_llm_model(cleaned_settings["llm_provider"]),
        ),
        cleaned_settings["llm_provider"],
    )
    cleaned_settings["llm_timeout_seconds"] = _coerce_int(
        settings.get("llm_timeout_seconds", DEFAULT_LLM_TIMEOUT_SECONDS),
        default=DEFAULT_LLM_TIMEOUT_SECONDS,
        minimum=MIN_LLM_TIMEOUT_SECONDS,
        maximum=MAX_LLM_TIMEOUT_SECONDS,
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
    cleaned_settings["tts_voice_name"] = _coerce_string(
        settings.get("tts_voice_name", DEFAULT_SETTINGS["tts_voice_name"]),
        default=str(DEFAULT_SETTINGS["tts_voice_name"]),
    )
    cleaned_settings["tts_rate"] = _coerce_int(
        settings.get("tts_rate", DEFAULT_SETTINGS["tts_rate"]),
        default=int(DEFAULT_SETTINGS["tts_rate"]),
        minimum=-10,
        maximum=10,
    )
    cleaned_settings["tts_volume"] = _coerce_int(
        settings.get("tts_volume", DEFAULT_SETTINGS["tts_volume"]),
        default=int(DEFAULT_SETTINGS["tts_volume"]),
        minimum=0,
        maximum=100,
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


def _coerce_optional_bool(value: Any) -> bool | None:
    """Convert boolean-like values or preserve None when unset."""
    if value is None:
        return None

    if isinstance(value, str) and not value.strip():
        return None

    return _coerce_bool(value)


def _coerce_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    """Convert a value into a bounded integer using a safe fallback."""
    try:
        parsed_value = int(value)
    except (TypeError, ValueError):
        return default

    return max(minimum, min(maximum, parsed_value))


def _coerce_string(value: Any, default: str) -> str:
    """Convert a value into a cleaned string with a safe default."""
    cleaned_value = normalize_text(str(value))
    return cleaned_value or default


def _coerce_llm_provider(value: Any) -> str:
    """Convert provider-like values into one of the supported LLM provider labels."""
    cleaned_value = normalize_text(str(value)).lower()
    if cleaned_value in {"xai", "groq"}:
        return cleaned_value
    return "auto"


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


# TODO: Add support for named assistant profiles when multi-user setups are needed.
