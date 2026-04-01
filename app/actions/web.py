"""Web actions for opening websites and performing simple searches."""

from urllib.parse import quote_plus
import webbrowser

from app.config import DEFAULT_WEBSITE_ENTRIES
from app.services.database import load_website_aliases
from app.utils.helpers import build_result


def open_website(target: str) -> dict[str, object]:
    """Open a supported website in the default browser."""
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
        return build_result(
            False,
            f"I do not know that website yet: '{target}'. Add it to the website_aliases table in MySQL or use a direct URL.",
            None,
        )

    url = cleaned_target
    if not url.startswith(("http://", "https://")):
        url = f"https://{url.lstrip('/')}"
    return _open_in_browser(url, f"Opening {target.strip()}.")


def search_google(query: str) -> dict[str, object]:
    """Search Google in the default browser."""
    cleaned_query = query.strip()
    if not cleaned_query:
        return build_result(False, "Please provide a Google search query.", None)

    url = f"https://www.google.com/search?q={quote_plus(cleaned_query)}"
    return _open_in_browser(url, f"Searching Google for {cleaned_query}.")


def search_youtube(query: str) -> dict[str, object]:
    """Search YouTube in the default browser."""
    cleaned_query = query.strip()
    if not cleaned_query:
        return build_result(False, "Please provide a YouTube search query.", None)

    url = f"https://www.youtube.com/results?search_query={quote_plus(cleaned_query)}"
    return _open_in_browser(url, f"Searching YouTube for {cleaned_query}.")


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
        }
        for entry in DEFAULT_WEBSITE_ENTRIES
    }


# TODO: Add a database-backed generic search action if you want more search engines.
