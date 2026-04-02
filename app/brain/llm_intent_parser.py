"""Optional xAI-backed intent parsing using tool-calling constraints."""

from __future__ import annotations

from typing import Any

from app.brain.tool_definitions import get_select_intent_tool, normalize_tool_call_to_intent
from app.config import LLM_ALLOWED_INTENTS, get_llm_api_key
from app.models.website_aliases import DEFAULT_WEBSITE_ENTRIES, load_website_aliases
from app.services.llm_service import request_intent_tool_call
from app.utils.helpers import normalize_text


def parse_intent_with_llm(
    text: str,
    settings: dict[str, Any],
    app_registry: dict[str, Any] | None = None,
    logger: Any | None = None,
) -> dict[str, str] | None:
    """Return a normalized intent from the xAI model, or None when unavailable."""
    if not _llm_parser_enabled(settings):
        return None

    raw_text = normalize_text(text)
    if not raw_text:
        return None

    try:
        tool_call = request_intent_tool_call(
            messages=_build_messages(raw_text, app_registry),
            tools=[get_select_intent_tool()],
            settings=settings,
            logger=logger,
        )
    except Exception as error:
        if logger is not None:
            logger.warning("LLM intent parsing raised an unexpected error: %s", error)
        return None

    if not isinstance(tool_call, dict):
        return None

    return normalize_tool_call_to_intent(
        raw_text=raw_text,
        tool_name=str(tool_call.get("name", "")),
        tool_arguments=tool_call.get("arguments"),
    )


def _llm_parser_enabled(settings: dict[str, Any]) -> bool:
    """Return True when LLM parsing should be attempted for unknown commands."""
    if "llm_parser_enabled" in settings:
        return bool(settings.get("llm_parser_enabled"))

    return bool(get_llm_api_key(str(settings.get("llm_provider", "auto"))))


def _build_messages(raw_text: str, app_registry: dict[str, Any] | None) -> list[dict[str, str]]:
    """Build the system and user messages sent to the LLM."""
    app_aliases, folder_aliases = _extract_registry_aliases(app_registry)
    website_aliases = _get_website_aliases()
    system_prompt = (
        "You are an intent selector for a local desktop assistant. "
        "Choose exactly one supported tool call when the request matches an allowed action. "
        "If nothing matches, return no tool call. "
        "Never invent unsupported actions. "
        "Use alias names as targets, not executable paths. "
        "For shutdown or restart requests, choose the exact corresponding intent."
        f"\nAllowed intents: {', '.join(LLM_ALLOWED_INTENTS)}."
        f"\nKnown app aliases: {', '.join(app_aliases) or 'none'}."
        f"\nKnown folder aliases: {', '.join(folder_aliases) or 'none'}."
        f"\nKnown website aliases: {', '.join(website_aliases) or 'none'}."
    )
    user_prompt = (
        "Parse this user request into one allowed intent tool call if possible.\n"
        f"User request: {raw_text}"
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _extract_registry_aliases(app_registry: dict[str, Any] | None) -> tuple[list[str], list[str]]:
    """Return sorted app and folder alias names from the current registry."""
    registry = app_registry or {}
    app_aliases = sorted(_extract_alias_keys(registry.get("apps")))
    folder_aliases = sorted(_extract_alias_keys(registry.get("folders")))
    return app_aliases, folder_aliases


def _extract_alias_keys(value: Any) -> list[str]:
    """Return sorted normalized alias keys from a registry section."""
    if not isinstance(value, dict):
        return []

    aliases: list[str] = []
    for alias in value.keys():
        cleaned_alias = normalize_text(str(alias)).lower()
        if cleaned_alias and cleaned_alias not in aliases:
            aliases.append(cleaned_alias)
    return aliases


def _get_website_aliases() -> list[str]:
    """Return website aliases from storage or the default config fallback."""
    stored_aliases = load_website_aliases()
    if stored_aliases:
        return sorted(stored_aliases.keys())

    return sorted(str(entry["alias"]).lower() for entry in DEFAULT_WEBSITE_ENTRIES)


# TODO: Include optional few-shot examples if Grok needs more reliable phrasing support.
