"""General helper functions for shared text and result handling tasks."""

from typing import Any


def normalize_text(text: str) -> str:
    """Return trimmed text with repeated spaces collapsed."""
    return " ".join(text.strip().split())


def build_result(
    success: bool,
    message: str,
    data: Any = None,
) -> dict[str, Any]:
    """Return a consistent result dictionary for command handlers."""
    return {
        "success": success,
        "message": message,
        "data": data,
    }


def looks_like_url(text: str) -> bool:
    """Return True when text appears to be a website URL or domain."""
    normalized = normalize_text(text).lower()
    if not normalized:
        return False

    if normalized.startswith(("http://", "https://", "www.")):
        return True

    return "." in normalized and " " not in normalized


# TODO: Add more reusable validators as more commands are supported.
