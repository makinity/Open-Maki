"""Wake word detection helpers for Maki."""

from __future__ import annotations

from app.utils.helpers import normalize_text

DEFAULT_WAKE_PHRASES = [
    "hey maki",
    "hi maki",
    "ok maki",
    "okay maki",
]


def detect_wake_phrase(
    text: str,
    wake_phrases: list[str] | None = None,
) -> tuple[bool, str]:
    """
    Detect whether text starts with a wake phrase.

    Returns:
        tuple[bool, str]:
            - matched: True if a wake phrase was found
            - remainder: command text after removing the wake phrase
    """
    cleaned = normalize_text(text)
    phrases = _expand_wake_phrases(wake_phrases or DEFAULT_WAKE_PHRASES)

    if not cleaned:
        return False, ""

    for phrase in phrases:
        if cleaned == phrase:
            return True, ""

        if cleaned.startswith(f"{phrase} "):
            remainder = cleaned[len(phrase) :].strip()
            return True, remainder

        if _is_partial_wake_phrase(cleaned, phrase):
            return True, ""

    return False, cleaned


def _expand_wake_phrases(wake_phrases: list[str]) -> list[str]:
    """Return cleaned wake phrases plus a few practical spoken variants."""
    expanded_phrases: list[str] = []

    for phrase in wake_phrases:
        normalized_phrase = normalize_text(phrase)
        if not normalized_phrase:
            continue

        for candidate in _expand_single_phrase(normalized_phrase):
            if candidate not in expanded_phrases:
                expanded_phrases.append(candidate)

    return sorted(expanded_phrases, key=len, reverse=True)


def _expand_single_phrase(phrase: str) -> list[str]:
    """Return a wake phrase plus simple text-recognition variants."""
    variants = [phrase]

    if "maki" in phrase and "makibot" not in phrase and "maki bot" not in phrase:
        variants.append(phrase.replace("maki", "makibot"))
        variants.append(phrase.replace("maki", "maki bot"))
        variants.append(phrase.replace("maki", "macky"))
        variants.append(phrase.replace("maki", "mackie"))

    if "makibot" in phrase:
        variants.append(phrase.replace("makibot", "maki bot"))
        variants.append(phrase.replace("makibot", "maki"))

    if "maki bot" in phrase:
        variants.append(phrase.replace("maki bot", "makibot"))
        variants.append(phrase.replace("maki bot", "maki"))

    return [normalize_text(item) for item in variants if normalize_text(item)]


def _is_partial_wake_phrase(text: str, phrase: str) -> bool:
    """Return True when text looks like a clipped beginning of a wake phrase."""
    if not text or len(text) < 3:
        return False

    if not phrase.startswith(text):
        return False

    text_words = text.split()
    phrase_words = phrase.split()
    if len(text_words) > len(phrase_words):
        return False

    return True
