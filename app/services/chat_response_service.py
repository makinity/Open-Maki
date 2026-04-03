"""LLM-backed helpers for conversational and friendly assistant responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.config import BOT_NAME, get_llm_api_key
from app.services.llm_service import request_text_response
from app.utils.helpers import normalize_text


def build_startup_greeting(
    settings: dict[str, Any],
    knowledge_text: str = "",
    knowledge_profile: dict[str, str] | None = None,
    logger: Any | None = None,
) -> str | None:
    """Return a short Groq-generated startup greeting for the owner."""
    if not get_llm_api_key("groq"):
        return None

    profile = knowledge_profile or {}
    preferred_title = normalize_text(str(profile.get("preferred_title", ""))) or "sir"
    startup_preference = normalize_text(str(profile.get("startup_greeting", "")))
    time_of_day = _get_time_of_day_label()
    request_settings = dict(settings)
    request_settings["llm_provider"] = "groq"

    user_prompt = (
        f"Generate one fresh spoken startup greeting for {BOT_NAME} as a session begins. "
        f"It is currently {time_of_day}. "
        f"Address the owner as {preferred_title}. "
        f"Refer to the assistant as {BOT_NAME}. "
        "Use the knowledge context when it helps. "
        "Be respectful, warm, polished, and natural. "
        "Return one or two short spoken sentences with no markdown, no quotes, and no emojis. "
        "Make it sound personal and intelligent, not generic. "
        f"Include that {BOT_NAME} is ready to help. "
        "Do not reply with only a short fixed salutation like 'Good day, sir.' "
        "Do not mention APIs, prompts, knowledge files, or boot/loading details."
    )
    if startup_preference:
        user_prompt = (
            f"{user_prompt} Treat this preferred startup style as inspiration only and expand beyond it: {startup_preference}."
        )

    messages = [
        {
            "role": "system",
            "content": _build_system_prompt(knowledge_text, profile),
        },
        {
            "role": "user",
            "content": user_prompt,
        },
    ]
    greeting = request_text_response(
        messages=messages,
        settings=request_settings,
        logger=logger,
        temperature=0.7,
    )
    return _finalize_startup_greeting(
        greeting=greeting,
        preferred_title=preferred_title,
        startup_preference=startup_preference,
    )


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


def _finalize_startup_greeting(
    greeting: str | None,
    preferred_title: str,
    startup_preference: str,
) -> str | None:
    """Normalize a startup greeting and expand overly generic outputs."""
    cleaned_greeting = normalize_text(greeting)
    if not cleaned_greeting:
        return None

    normalized_greeting = _normalize_phrase(cleaned_greeting)
    normalized_preference = _normalize_phrase(startup_preference)
    if len(cleaned_greeting.split()) <= 4 or (
        normalized_preference and normalized_greeting == normalized_preference
    ):
        return _append_ready_clause(cleaned_greeting, preferred_title)

    return cleaned_greeting


def _append_ready_clause(greeting: str, preferred_title: str) -> str:
    """Expand a too-short greeting into a fuller startup line."""
    base_greeting = greeting.rstrip(".!? ").strip()
    title_suffix = f", {preferred_title}" if preferred_title else ""
    return f"{base_greeting}. {BOT_NAME} is ready to help you today{title_suffix}."


def _normalize_phrase(value: str) -> str:
    """Normalize punctuation and spacing for lightweight phrase comparisons."""
    return "".join(char.lower() for char in value if char.isalnum() or char.isspace()).strip()


def _get_time_of_day_label() -> str:
    """Return a simple local time-of-day label for startup greetings."""
    hour = datetime.now().hour
    if hour < 12:
        return "morning"
    if hour < 18:
        return "afternoon"
    return "evening"


# TODO: Add recent history context when multi-turn chat memory becomes necessary.
