"""Rule-based intent parser backed by database-stored command templates."""

import re

from app.config import DEFAULT_COMMAND_PATTERNS, WEBSITE_ALIASES
from app.services.database import load_command_patterns, load_website_aliases
from app.utils.helpers import looks_like_url, normalize_text


def parse_intent(text: str) -> dict[str, str]:
    """Parse raw user text into a consistent intent dictionary."""
    raw_text = normalize_text(text or "")
    normalized_text = raw_text.lower()

    if not normalized_text:
        return _build_intent("unknown", "", raw_text)

    for pattern in _load_active_patterns():
        matched_target = _match_template(raw_text, str(pattern.get("phrase_template", "")))
        if matched_target is None:
            continue

        intent_name = str(pattern.get("intent", "unknown")).strip() or "unknown"
        fixed_target = _clean_target(str(pattern.get("fixed_target", "")))
        resolved_target = matched_target or fixed_target

        if intent_name == "open_target":
            return _build_open_target_intent(resolved_target, raw_text)

        return _build_intent(intent_name, resolved_target, raw_text)

    if looks_like_url(raw_text) or normalized_text in _load_website_alias_map():
        return _build_intent("open_website", raw_text, raw_text)

    return _build_intent("unknown", raw_text, raw_text)


def _build_open_target_intent(target: str, raw_text: str) -> dict[str, str]:
    """Choose whether an open-style command targets a website or an app."""
    normalized_target = target.lower()
    if looks_like_url(target) or normalized_target in _load_website_alias_map():
        return _build_intent("open_website", target, raw_text)

    return _build_intent("open_app", target, raw_text)


def _load_active_patterns() -> list[dict[str, object]]:
    """Return command templates from MySQL, or fallback defaults when unavailable."""
    patterns = load_command_patterns()
    if patterns:
        return patterns

    return [dict(pattern) for pattern in DEFAULT_COMMAND_PATTERNS]


def _match_template(text: str, template: str) -> str | None:
    """Return a matched target from one command template or None when it does not match."""
    normalized_template = normalize_text(template)
    if not normalized_template:
        return None

    if "{target}" not in normalized_template:
        if re.fullmatch(re.escape(normalized_template), text, flags=re.IGNORECASE):
            return ""
        return None

    pattern = re.escape(normalized_template).replace(r"\{target\}", r"(.+)")
    match = re.fullmatch(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None

    return _clean_target(match.group(1))


def _load_website_alias_map() -> dict[str, str]:
    """Return website aliases from MySQL or the default config fallback."""
    website_entries = load_website_aliases()
    if website_entries:
        return {alias: details["url"] for alias, details in website_entries.items()}

    return dict(WEBSITE_ALIASES)


def _clean_target(value: str) -> str:
    """Trim a target value and remove simple wrapping punctuation."""
    cleaned_value = normalize_text(value)
    cleaned_value = cleaned_value.strip(" \"'.,!?")
    return normalize_text(cleaned_value)


def _build_intent(intent: str, target: str, raw_text: str) -> dict[str, str]:
    """Build the consistent intent structure used by the assistant."""
    return {
        "intent": intent,
        "target": target,
        "raw_text": raw_text,
    }


# TODO: Add richer template fields if you want command extraction beyond one {target}.
