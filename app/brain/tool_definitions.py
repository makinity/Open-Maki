"""Tool definitions and normalization helpers for LLM intent selection."""

from __future__ import annotations

import json
from typing import Any

from app.config import LLM_ALLOWED_INTENTS
from app.utils.helpers import normalize_text

SELECT_INTENT_TOOL_NAME = "select_intent"

TARGET_REQUIRED_INTENTS = {
    "open_app",
    "open_website",
    "search_google",
    "search_youtube",
    "create_folder",
    "open_folder",
    "type_text",
}

FIXED_TARGET_INTENTS = {
    "shutdown_computer": "computer",
    "restart_computer": "computer",
}

NO_TARGET_INTENTS = {
    "tell_time",
    "tell_date",
    "list_commands",
    "help",
    "exit_bot",
}


def get_select_intent_tool() -> dict[str, Any]:
    """Return the constrained tool schema exposed to the LLM."""
    return {
        "type": "function",
        "function": {
            "name": SELECT_INTENT_TOOL_NAME,
            "description": "Choose the single supported assistant intent that best matches the user request.",
            "parameters": {
                "type": "object",
                "properties": {
                    "intent": {
                        "type": "string",
                        "enum": list(LLM_ALLOWED_INTENTS),
                        "description": "The allowed assistant intent to run.",
                    },
                    "target": {
                        "type": "string",
                        "description": "The user-facing alias or text target when the chosen intent needs one.",
                    },
                },
                "required": ["intent"],
                "additionalProperties": False,
            },
        },
    }


def normalize_tool_call_to_intent(
    raw_text: str,
    tool_name: str,
    tool_arguments: Any,
) -> dict[str, str] | None:
    """Normalize one LLM tool call into the existing assistant intent dict."""
    if normalize_text(tool_name) != SELECT_INTENT_TOOL_NAME:
        return None

    arguments = _coerce_arguments(tool_arguments)
    if not isinstance(arguments, dict):
        return None

    intent_name = normalize_text(str(arguments.get("intent", "")))
    if intent_name not in LLM_ALLOWED_INTENTS:
        return None

    if intent_name in FIXED_TARGET_INTENTS:
        target = FIXED_TARGET_INTENTS[intent_name]
    elif intent_name in NO_TARGET_INTENTS:
        target = ""
    else:
        target = normalize_text(str(arguments.get("target", "")))
        if intent_name in TARGET_REQUIRED_INTENTS and not target:
            return None

    return {
        "intent": intent_name,
        "target": target,
        "raw_text": normalize_text(raw_text),
    }


def _coerce_arguments(tool_arguments: Any) -> dict[str, Any] | None:
    """Return a dictionary of tool arguments from JSON text or a dict."""
    if isinstance(tool_arguments, dict):
        return tool_arguments

    if not isinstance(tool_arguments, str):
        return None

    try:
        parsed_arguments = json.loads(tool_arguments)
    except json.JSONDecodeError:
        return None

    if isinstance(parsed_arguments, dict):
        return parsed_arguments

    return None


# TODO: Support richer tool outputs if Maki later needs structured entities.
