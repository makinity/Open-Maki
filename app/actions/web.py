"""Web actions for opening websites and performing database-driven site searches."""

from urllib.parse import quote_plus
import webbrowser

from app.models.website_aliases import DEFAULT_WEBSITE_ENTRIES, load_website_aliases
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


# TODO: Add admin helpers for creating website aliases directly from the assistant.
