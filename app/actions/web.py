"""Web actions for opening websites and performing simple searches."""

from urllib.parse import quote_plus
import webbrowser

from app.utils.helpers import build_result

SUPPORTED_WEBSITES: dict[str, tuple[str, str]] = {
    "youtube": ("YouTube", "https://www.youtube.com"),
    "gmail": ("Gmail", "https://mail.google.com"),
    "google": ("Google", "https://www.google.com"),
    "facebook": ("Facebook", "https://www.facebook.com"),
}


def open_website(target: str) -> dict[str, object]:
    """Open a supported website in the default browser."""
    cleaned_target = target.strip().lower()
    if not cleaned_target:
        return build_result(False, "Please provide a website name.", None)

    website = SUPPORTED_WEBSITES.get(cleaned_target)
    if website is None:
        return build_result(
            False,
            f"I do not know that website yet: '{target}'. Supported sites are YouTube, Gmail, Google, and Facebook.",
            None,
        )

    site_name, url = website
    return _open_in_browser(url, f"Opening {site_name}.")


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


# TODO: Add support for more website aliases if the command list grows.
