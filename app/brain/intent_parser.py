"""Rule-based intent parser for the supported MakiBot Phase 3 commands."""

import re

from app.config import WEBSITE_ALIASES
from app.utils.helpers import looks_like_url, normalize_text

SUPPORTED_WEB_TARGETS = {
    "youtube",
    "gmail",
    "google",
    "facebook",
}

_CONFIRM_YES_PATTERNS = [
    r"yes",
    r"yes please",
    r"confirm",
    r"confirm it",
    r"do it",
]

_CONFIRM_NO_PATTERNS = [
    r"no",
    r"no thanks",
    r"cancel",
    r"never mind",
    r"stop that",
]

_EXIT_PATTERNS = [
    r"exit",
    r"exit bot",
    r"quit",
    r"quit bot",
    r"goodbye",
    r"bye",
]

_TIME_PATTERNS = [
    r"time",
    r"current time",
    r"what time is it",
    r"tell me the time",
]

_DATE_PATTERNS = [
    r"date",
    r"today(?:'s)? date",
    r"what date is it",
    r"what is today(?:'s)? date",
    r"tell me the date",
]

_HELP_PATTERNS = [
    r"help",
    r"what can you do",
    r"what do you do",
    r"how can you help",
]

_LIST_COMMAND_PATTERNS = [
    r"list commands",
    r"show commands",
    r"show me the commands",
    r"what commands do you know",
]


def parse_intent(text: str) -> dict[str, str]:
    """Parse raw user text into a consistent intent dictionary."""
    raw_text = normalize_text(text or "")
    normalized_text = raw_text.lower()

    if not normalized_text:
        return _build_intent("unknown", "", raw_text)

    if _matches(normalized_text, _CONFIRM_YES_PATTERNS):
        return _build_intent("confirm_yes", "", raw_text)

    if _matches(normalized_text, _CONFIRM_NO_PATTERNS):
        return _build_intent("confirm_no", "", raw_text)

    if _matches(normalized_text, _EXIT_PATTERNS):
        return _build_intent("exit_bot", "", raw_text)

    if _matches(normalized_text, _TIME_PATTERNS):
        return _build_intent("tell_time", "", raw_text)

    if _matches(normalized_text, _DATE_PATTERNS):
        return _build_intent("tell_date", "", raw_text)

    if _matches(normalized_text, _HELP_PATTERNS):
        return _build_intent("help", "", raw_text)

    if _matches(normalized_text, _LIST_COMMAND_PATTERNS):
        return _build_intent("list_commands", "", raw_text)

    if _matches(normalized_text, [r"shutdown computer", r"shut down computer", r"turn off computer"]):
        return _build_intent("shutdown_computer", "computer", raw_text)

    if _matches(normalized_text, [r"restart computer", r"reboot computer"]):
        return _build_intent("restart_computer", "computer", raw_text)

    target = _extract_target(
        raw_text,
        [
            r"search youtube for (.+)",
            r"search on youtube for (.+)",
            r"youtube (.+)",
        ],
    )
    if target:
        return _build_intent("search_youtube", target, raw_text)

    target = _extract_target(
        raw_text,
        [
            r"search google for (.+)",
            r"google (.+)",
            r"search for (.+)",
        ],
    )
    if target:
        return _build_intent("search_google", target, raw_text)

    target = _extract_target(
        raw_text,
        [
            r"make(?: me)?(?: a)? folder(?: called)? (.+)",
            r"create(?: me)?(?: a)? folder(?: called)? (.+)",
            r"new folder (.+)",
        ],
    )
    if target:
        return _build_intent("create_folder", target, raw_text)

    target = _extract_target(
        raw_text,
        [
            r"open folder (.+)",
            r"go to folder (.+)",
        ],
    )
    if target:
        return _build_intent("open_folder", target, raw_text)

    target = _extract_target(raw_text, [r"type (.+)", r"write (.+)"])
    if target:
        return _build_intent("type_text", target, raw_text)

    target = _extract_target(raw_text, [r"open website (.+)", r"visit (.+)", r"go to (.+)"])
    if target:
        return _build_open_target_intent(target, raw_text)

    target = _extract_target(raw_text, [r"open (.+)", r"launch (.+)", r"start (.+)"])
    if target:
        return _build_open_target_intent(target, raw_text)

    if looks_like_url(raw_text) or normalized_text in WEBSITE_ALIASES or normalized_text in SUPPORTED_WEB_TARGETS:
        return _build_intent("open_website", raw_text, raw_text)

    return _build_intent("unknown", raw_text, raw_text)


def _build_open_target_intent(target: str, raw_text: str) -> dict[str, str]:
    """Choose whether an open-style command targets a website or an app."""
    normalized_target = target.lower()
    if (
        looks_like_url(target)
        or normalized_target in WEBSITE_ALIASES
        or normalized_target in SUPPORTED_WEB_TARGETS
    ):
        return _build_intent("open_website", target, raw_text)

    return _build_intent("open_app", target, raw_text)


def _extract_target(text: str, patterns: list[str]) -> str:
    """Return the first extracted target that matches one of the patterns."""
    for pattern in patterns:
        match = re.fullmatch(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue

        return _clean_target(match.group(1))

    return ""


def _clean_target(value: str) -> str:
    """Trim a target value and remove simple wrapping punctuation."""
    cleaned_value = normalize_text(value)
    cleaned_value = cleaned_value.strip(" \"'.,!?")
    return normalize_text(cleaned_value)


def _matches(text: str, patterns: list[str]) -> bool:
    """Return True when the text matches any of the provided patterns."""
    return any(re.fullmatch(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _build_intent(intent: str, target: str, raw_text: str) -> dict[str, str]:
    """Build the consistent intent structure used by the assistant."""
    return {
        "intent": intent,
        "target": target,
        "raw_text": raw_text,
    }


# TODO: Expand parsing rules with more conversational variations over time.
