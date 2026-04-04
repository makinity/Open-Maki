"""Web actions for opening websites and performing database-driven site searches."""

import json
from urllib.parse import quote_plus, urlparse
import webbrowser

from app.models.website_aliases import DEFAULT_WEBSITE_ENTRIES, load_website_aliases
from app.services.llm_service import request_text_response
from app.utils.helpers import build_result


def open_website(
    target: str,
    settings: dict[str, object] | None = None,
    logger: object | None = None,
) -> dict[str, object]:
    """Open a supported website using aliases first, then a safe LLM inference fallback."""
    cleaned_target = target.strip().lower()
    if not cleaned_target:
        return build_result(False, "Please provide a website name.", None)

    websites = _load_supported_websites()
    website = websites.get(cleaned_target)
    if website is not None:
        site_name = str(website.get("name", cleaned_target.title()))
        url = str(website.get("url", "")).strip()
        if not url:
            return build_result(False, f"The website alias '{target}' does not have a valid URL.", None)
        return _open_in_browser(url, f"Opening {site_name}.")

    if "." not in cleaned_target and not cleaned_target.startswith(("http://", "https://", "www.")):
        inferred_website = _infer_website(cleaned_target, settings=settings or {}, logger=logger)
        if inferred_website is not None:
            return _open_in_browser(
                inferred_website["url"],
                f"Opening {inferred_website['name']}.",
            )

        return build_result(
            False,
            f"I could not identify the website '{target}'. Add it to the website_aliases table or use a direct URL.",
            None,
        )

    url = cleaned_target
    if not url.startswith(("http://", "https://")):
        url = f"https://{url.lstrip('/')}"
    return _open_in_browser(url, f"Opening {target.strip()}.")


def search_google(query: str) -> dict[str, object]:
    """Search Google in the default browser."""
    return search_website("google", query)


def search_youtube(query: str) -> dict[str, object]:
    """Search YouTube in the default browser."""
    return search_website("youtube", query)


def search_website(site: str, query: str) -> dict[str, object]:
    """Search one website alias using its database-backed search URL template."""
    cleaned_site = site.strip().lower()
    cleaned_query = query.strip()
    if not cleaned_site:
        return build_result(False, "Please provide a website alias to search.", None)
    if not cleaned_query:
        return build_result(False, "Please provide a search query.", None)

    websites = _load_supported_websites()
    website = websites.get(cleaned_site)
    if website is None:
        return build_result(
            False,
            f"I do not know that website yet: '{site}'. Add it to the website_aliases table in MySQL.",
            None,
        )

    site_name = str(website.get("name", cleaned_site.title()))
    search_url_template = str(website.get("search_url_template", "")).strip()
    if not search_url_template:
        return build_result(
            False,
            f"{site_name} does not have a search URL template yet. Add one in the website_aliases table.",
            None,
        )

    encoded_query = quote_plus(cleaned_query)
    if "{query}" in search_url_template:
        url = search_url_template.replace("{query}", encoded_query)
    else:
        joiner = "&" if "?" in search_url_template else "?"
        url = f"{search_url_template}{joiner}q={encoded_query}"

    return _open_in_browser(url, f"Searching {site_name} for {cleaned_query}.")


def _open_in_browser(url: str, success_message: str) -> dict[str, object]:
    """Open a URL in the default browser with safe error handling."""
    try:
        opened = webbrowser.open_new_tab(url)
    except Exception as error:
        return build_result(False, f"Failed to open the browser: {error}", None)

    if opened is False:
        return build_result(False, "The browser did not accept the request.", None)

    return build_result(True, success_message, None)


def _load_supported_websites() -> dict[str, dict[str, str]]:
    """Return website aliases from MySQL or the default config fallback."""
    database_aliases = load_website_aliases()
    if database_aliases:
        return database_aliases

    return {
        str(entry["alias"]): {
            "name": str(entry["name"]),
            "url": str(entry["url"]),
            "search_url_template": str(entry.get("search_url_template", "")),
        }
        for entry in DEFAULT_WEBSITE_ENTRIES
    }


def _infer_website(
    target: str,
    settings: dict[str, object],
    logger: object | None = None,
) -> dict[str, str] | None:
    """Infer one official homepage URL for a plain-language website target."""
    response_text = request_text_response(
        messages=[
            {
                "role": "system",
                "content": (
                    "You identify official website homepages for a desktop assistant. "
                    "Return JSON only with keys 'name' and 'url'. "
                    "Use the service or brand's main homepage, not a search page, article, profile, or app store page. "
                    "If you are not confident, return {\"name\": \"\", \"url\": \"\"}."
                ),
            },
            {
                "role": "user",
                "content": f"Website target: {target}",
            },
        ],
        settings=settings,
        logger=logger,
        temperature=0,
    )
    if not response_text:
        return None

    parsed_payload = _parse_inferred_website_response(response_text)
    if parsed_payload is None:
        if logger is not None and hasattr(logger, "debug"):
            logger.debug("Website inference returned an unusable payload for '%s': %s", target, response_text)
        return None

    return parsed_payload


def _parse_inferred_website_response(response_text: str) -> dict[str, str] | None:
    """Return a normalized website payload from one LLM text response."""
    normalized_text = response_text.strip()
    if normalized_text.startswith("```"):
        normalized_text = normalized_text.strip("`")
        if normalized_text.lower().startswith("json"):
            normalized_text = normalized_text[4:].strip()

    parsed_json: dict[str, object] | None = None
    try:
        maybe_json = json.loads(normalized_text)
        if isinstance(maybe_json, dict):
            parsed_json = maybe_json
    except json.JSONDecodeError:
        parsed_json = None

    if parsed_json is not None:
        inferred_url = str(parsed_json.get("url", "")).strip()
        inferred_name = str(parsed_json.get("name", "")).strip()
        if not _is_valid_website_url(inferred_url):
            return None
        return {
            "name": inferred_name or _display_name_from_url(inferred_url),
            "url": inferred_url,
        }

    if _is_valid_website_url(normalized_text):
        return {
            "name": _display_name_from_url(normalized_text),
            "url": normalized_text,
        }

    return None


def _is_valid_website_url(url: str) -> bool:
    """Return True when the inferred URL is a plausible HTTP(S) homepage."""
    try:
        parsed_url = urlparse(url)
    except Exception:
        return False

    if parsed_url.scheme not in {"http", "https"}:
        return False

    if not parsed_url.netloc:
        return False

    return True


def _display_name_from_url(url: str) -> str:
    """Return a simple display label derived from a homepage URL."""
    parsed_url = urlparse(url)
    hostname = parsed_url.netloc.lower()
    if hostname.startswith("www."):
        hostname = hostname[4:]

    primary_label = hostname.split(".", 1)[0].replace("-", " ").strip()
    if not primary_label:
        return "that website"

    return primary_label.title()


# TODO: Add admin helpers for creating website aliases directly from the assistant.
