"""Typing actions with a safe preview-first default behavior."""

from typing import Any

from app.utils.helpers import build_result

try:
    import pyautogui
except ImportError:
    pyautogui = None


def type_text(text: str, live_mode: bool = False) -> dict[str, Any]:
    """Type text with automation when enabled, otherwise return a safe preview."""
    cleaned_text = text.strip()
    if not cleaned_text:
        return build_result(False, "Please provide text to type.", {"status": "invalid_input"})

    if not live_mode:
        return build_result(
            True,
            "Typing preview ready. Enable typing_live_mode in settings to type for real.",
            {"status": "preview", "typed": False, "text": cleaned_text},
        )

    if pyautogui is None:
        return build_result(False, "pyautogui is not installed, so live typing is unavailable.", {"status": "not_available"})

    try:
        pyautogui.write(cleaned_text, interval=0.03)
    except Exception as error:
        return build_result(False, f"Failed to type text: {error}", {"status": "error"})

    return build_result(True, "Typing completed.", {"status": "completed", "typed": True, "text": cleaned_text})


# TODO: Add a countdown before live typing begins.
