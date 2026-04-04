"""Rule-based intent parser backed by database-stored command templates."""

import re

from app.models.app_aliases import BUILTIN_APP_ENTRIES, load_app_alias_entries
from app.models.command_patterns import DEFAULT_COMMAND_PATTERNS, load_command_patterns
from app.models.website_aliases import (
    DEFAULT_WEBSITE_ENTRIES,
    WEBSITE_ALIASES,
    load_website_aliases,
)
from app.utils.helpers import looks_like_url, normalize_text

_PLACEHOLDER_PATTERN = re.compile(r"\{([a-z_]+)\}")


def parse_intent(text: str) -> dict[str, str]:
    """Parse raw user text into a consistent intent dictionary."""
    raw_text = normalize_text(text or "")
    normalized_text = raw_text.lower()

    if not normalized_text:
        return _build_intent("unknown", "", raw_text)

    for pattern in _load_active_patterns():
        matched_values = _match_template(raw_text, str(pattern.get("phrase_template", "")))
        if matched_values is None:
            continue

        intent_name = str(pattern.get("intent", "unknown")).strip() or "unknown"
        fixed_target = _clean_target(str(pattern.get("fixed_target", "")))
        resolved_target = matched_values.get("target", "") or fixed_target

        if intent_name == "open_target":
            return _build_open_target_intent(resolved_target, raw_text)

        if intent_name == "search_website":
            search_intent = _build_site_search_intent(
                site=matched_values.get("site", ""),
                query=resolved_target,
                raw_text=raw_text,
            )
            if search_intent is None:
                continue
            return search_intent

        return _build_intent(intent_name, resolved_target, raw_text)

    if looks_like_url(raw_text) or normalized_text in _load_website_alias_map():
        return _build_intent("open_website", raw_text, raw_text)

    return _build_intent("unknown", raw_text, raw_text)


def _build_open_target_intent(target: str, raw_text: str) -> dict[str, str]:
    """Choose whether an open-style command targets a website, app, or an ambiguous fallback."""
    normalized_target = target.lower()
    if not normalized_target:
        return _build_intent("unknown", target, raw_text)

    if looks_like_url(target) or normalized_target in _load_website_alias_map():
        return _build_intent("open_website", target, raw_text)

    if normalized_target in _load_app_alias_map():
        return _build_intent("open_app", target, raw_text)

    return _build_intent("unknown", target, raw_text)


def _load_active_patterns() -> list[dict[str, object]]:
    """Return command templates from MySQL, or fallback defaults when unavailable."""
    merged_patterns: dict[str, dict[str, object]] = {}

    for pattern in load_command_patterns():
        phrase_template = normalize_text(str(pattern.get("phrase_template", "")))
        if phrase_template:
            merged_patterns[phrase_template] = dict(pattern)

    for pattern in DEFAULT_COMMAND_PATTERNS:
        phrase_template = normalize_text(str(pattern.get("phrase_template", "")))
        if phrase_template and phrase_template not in merged_patterns:
            merged_patterns[phrase_template] = dict(pattern)

    if not merged_patterns:
        return [dict(pattern) for pattern in DEFAULT_COMMAND_PATTERNS]

    return sorted(
        merged_patterns.values(),
        key=lambda pattern: (
            int(pattern.get("priority", 100)),
            -len(str(pattern.get("phrase_template", ""))),
        ),
    )


def _match_template(text: str, template: str) -> dict[str, str] | None:
    """Return placeholder values from one command template or None when it does not match."""
    normalized_template = normalize_text(template)
    if not normalized_template:
        return None

    placeholder_names = _PLACEHOLDER_PATTERN.findall(normalized_template)
    if not placeholder_names:
        if re.fullmatch(re.escape(normalized_template), text, flags=re.IGNORECASE):
            return {}
        return None

    pattern = re.escape(normalized_template)
    for placeholder_name in placeholder_names:
        pattern = pattern.replace(
            r"\{" + placeholder_name + r"\}",
            rf"(?P<{placeholder_name}>.+?)",
        )
    match = re.fullmatch(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None

    return {
        placeholder_name: _clean_target(match.group(placeholder_name))
        for placeholder_name in placeholder_names
    }


def _load_website_alias_map() -> dict[str, str]:
    """Return website aliases from MySQL or the default config fallback."""
    website_entries = load_website_aliases()
    if website_entries:
        return {alias: details["url"] for alias, details in website_entries.items()}

    return dict(WEBSITE_ALIASES)


def _load_app_alias_map() -> set[str]:
    """Return known app aliases from MySQL or the built-in config fallback."""
    try:
        app_entries = load_app_alias_entries()
    except Exception:
        app_entries = []

    if app_entries:
        return {str(entry.get("alias", "")).strip().lower() for entry in app_entries if str(entry.get("alias", "")).strip()}

    builtin_aliases: set[str] = set()
    for entry in BUILTIN_APP_ENTRIES:
        builtin_aliases.add(str(entry.get("name", "")).strip().lower())
        for alias in entry.get("aliases", []):
            normalized_alias = normalize_text(str(alias)).lower()
            if normalized_alias:
                builtin_aliases.add(normalized_alias)

    return builtin_aliases


def _build_site_search_intent(site: str, query: str, raw_text: str) -> dict[str, str] | None:
    """Return one concrete search intent when the website alias supports searching."""
    normalized_site = _clean_target(site).lower()
    cleaned_query = _clean_target(query)
    if not normalized_site or not cleaned_query:
        return None

    searchable_websites = _get_searchable_website_aliases()
    if normalized_site not in searchable_websites:
        return None

    if normalized_site == "google":
        return _build_intent("search_google", cleaned_query, raw_text)

    if normalized_site == "youtube":
        return _build_intent("search_youtube", cleaned_query, raw_text)

    return _build_intent("search_website", cleaned_query, raw_text, site=normalized_site)


def _get_searchable_website_aliases() -> set[str]:
    """Return website alias names that have a search URL template."""
    website_entries = load_website_aliases()
    if website_entries:
        return {
            alias
            for alias, details in website_entries.items()
            if str(details.get("search_url_template", "")).strip()
        }

    return {
        str(entry["alias"]).lower()
        for entry in DEFAULT_WEBSITE_ENTRIES
        if str(entry.get("search_url_template", "")).strip()
    }


def _clean_target(value: str) -> str:
    """Trim a target value and remove simple wrapping punctuation."""
    cleaned_value = normalize_text(value)
    cleaned_value = cleaned_value.strip(" \"'.,!?")
    return normalize_text(cleaned_value)


def _build_intent(intent: str, target: str, raw_text: str, site: str = "") -> dict[str, str]:
    """Build the consistent intent structure used by the assistant."""
    intent_data = {
        "intent": intent,
        "target": target,
        "raw_text": raw_text,
    }
    if site:
        intent_data["site"] = site
    return intent_data


# TODO: Add richer template fields if you want command extraction beyond one {target}.

