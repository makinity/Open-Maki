"""Transport helpers for calling xAI-compatible chat models with tool calling."""

from __future__ import annotations

from typing import Any

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None

from app.config import (
    DEFAULT_LLM_TIMEOUT_SECONDS,
    get_llm_api_key,
    get_llm_api_url,
    normalize_llm_model,
)


def request_intent_tool_call(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    settings: dict[str, Any],
    logger: Any | None = None,
) -> dict[str, Any] | None:
    """Request a single tool call from the configured xAI model."""
    provider = str(settings.get("llm_provider", "auto"))
    api_key = get_llm_api_key(provider)
    if not api_key or OpenAI is None:
        return None

    base_url = get_llm_api_url(provider)
    model = normalize_llm_model(str(settings.get("llm_model", "")), provider)
    timeout = _get_timeout_seconds(settings)

    try:
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0,
        )
    except Exception as error:
        if logger is not None:
            logger.warning("LLM intent parsing failed: %s", error)
        return None

    return _extract_first_tool_call(response)


def _extract_first_tool_call(response: Any) -> dict[str, Any] | None:
    """Return the first tool call from a chat completion response."""
    message = _get_choice_message(response)
    tool_calls = _read_value(message, "tool_calls")
    if not isinstance(tool_calls, list) or not tool_calls:
        return None

    tool_call = tool_calls[0]
    function_data = _read_value(tool_call, "function")
    if function_data is None:
        return None

    tool_name = _read_value(function_data, "name")
    tool_arguments = _read_value(function_data, "arguments")
    if not isinstance(tool_name, str):
        return None

    return {
        "name": tool_name,
        "arguments": tool_arguments,
    }


def _get_choice_message(response: Any) -> Any | None:
    """Return the message object from the first choice in a response."""
    choices = _read_value(response, "choices")
    if not isinstance(choices, list) or not choices:
        return None

    first_choice = choices[0]
    return _read_value(first_choice, "message")


def _read_value(value: Any, key: str) -> Any:
    """Read one attribute or dictionary key from a mixed SDK/mock object."""
    if value is None:
        return None

    if isinstance(value, dict):
        return value.get(key)

    return getattr(value, key, None)


def _get_timeout_seconds(settings: dict[str, Any]) -> int:
    """Return a safe timeout value for one LLM request."""
    try:
        parsed_timeout = int(settings.get("llm_timeout_seconds", DEFAULT_LLM_TIMEOUT_SECONDS))
    except (TypeError, ValueError):
        return DEFAULT_LLM_TIMEOUT_SECONDS

    if parsed_timeout < 1:
        return DEFAULT_LLM_TIMEOUT_SECONDS

    return parsed_timeout


# TODO: Add cached clients if request volume grows beyond simple assistant turns.
