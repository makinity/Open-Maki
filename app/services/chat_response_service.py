"""LLM-backed helpers for conversational and friendly assistant responses."""

from __future__ import annotations

from typing import Any

from app.services.llm_service import request_text_response
from app.utils.helpers import normalize_text


def build_chat_reply(
    user_text: str,
    settings: dict[str, Any],
    knowledge_text: str = "",
    knowledge_profile: dict[str, str] | None = None,
    logger: Any | None = None,
) -> str | None:
    """Return a conversational reply for non-command chat-like input."""
    cleaned_text = normalize_text(user_text)
    if not cleaned_text:
        return None

    messages = [
        {
            "role": "system",
            "content": _build_system_prompt(knowledge_text, knowledge_profile),
        },
        {
            "role": "user",
            "content": (
                "Reply as a friendly desktop assistant. "
                "Keep it brief and natural, and do not claim you executed any command.\n"
                f"User message: {cleaned_text}"
            ),
        },
    ]
    return request_text_response(messages=messages, settings=settings, logger=logger, temperature=0.5)


def build_kind_command_reply(
    user_text: str,
    intent: dict[str, str],
    result: dict[str, Any],
    settings: dict[str, Any],
    knowledge_text: str = "",
    knowledge_profile: dict[str, str] | None = None,
    logger: Any | None = None,
) -> str | None:
    """Return a short, kind rephrasing of an already-computed command result."""
    backend_message = normalize_text(str(result.get("message", "")))
    if not backend_message:
        return None

    messages = [
        {
            "role": "system",
            "content": _build_system_prompt(knowledge_text, knowledge_profile),
        },
        {
            "role": "user",
            "content": (
                "Rewrite this assistant response into one short spoken sentence. "
                "Be kind and natural. Keep the original meaning exactly. "
                "Do not invent actions, and do not remove warnings or confirmations.\n"
                f"User request: {normalize_text(user_text)}\n"
                f"Intent: {intent.get('intent', 'unknown')}\n"
                f"Backend response: {backend_message}"
            ),
        },
    ]
    return request_text_response(messages=messages, settings=settings, logger=logger, temperature=0.4)


def _build_system_prompt(
    knowledge_text: str,
    knowledge_profile: dict[str, str] | None,
) -> str:
    """Build the system prompt used for conversational replies."""
    profile = knowledge_profile or {}
    preferred_title = normalize_text(str(profile.get("preferred_title", "")))
    title_instruction = (
        f"Address the owner as {preferred_title} when it fits naturally. "
        if preferred_title
        else ""
    )
    knowledge_block = knowledge_text.strip() or "No extra knowledge file was provided."
    return (
        "You are Maki, a kind local desktop assistant. "
        "Be respectful, warm, and concise. "
        f"{title_instruction}"
        "Never pretend that you completed an action unless the backend already did it. "
        "Never override safety boundaries.\n"
        f"Knowledge:\n{knowledge_block}"
    )


# TODO: Add recent history context when multi-turn chat memory becomes necessary.
