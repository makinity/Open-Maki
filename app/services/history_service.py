"""Service helpers for loading and saving command history entries."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import DEFAULT_HISTORY_LIMIT, HISTORY_FILE


def load_history() -> list[dict[str, Any]]:
    """Load command history entries from disk."""
    data = _read_json_file(HISTORY_FILE)
    if not isinstance(data, list):
        return []

    return [item for item in data if isinstance(item, dict)]


def save_history(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Write command history entries to disk."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_FILE.open("w", encoding="utf-8") as file:
        json.dump(entries, file, indent=2)

    return entries


def add_history_entry(
    command_text: str,
    intent: dict[str, Any],
    result: dict[str, Any],
    history_limit: int = DEFAULT_HISTORY_LIMIT,
    source: str = "user",
) -> dict[str, Any]:
    """Append a single history entry to the JSON history file."""
    result_data = result.get("data")
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "source": source,
        "raw_text": str(intent.get("raw_text", command_text)),
        "intent": str(intent.get("intent", "unknown")),
        "target": str(intent.get("target", "")),
        "success": bool(result.get("success", False)),
        "status": _get_result_status(result),
        "message": str(result.get("message", "")),
        "data": _make_json_safe(result_data),
    }

    history = load_history()
    history.append(entry)

    if history_limit > 0:
        history = history[-history_limit:]

    save_history(history)
    return entry


def _get_result_status(result: dict[str, Any]) -> str:
    """Return a status label stored inside the result payload when present."""
    data = result.get("data")
    if isinstance(data, dict):
        status = data.get("status")
        if isinstance(status, str) and status.strip():
            return status.strip()

    return "completed" if bool(result.get("success", False)) else "failed"


def _make_json_safe(value: Any) -> Any:
    """Convert values into JSON-safe data for persistent history records."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, dict):
        return {str(key): _make_json_safe(item) for key, item in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_make_json_safe(item) for item in value]

    return str(value)


def _read_json_file(path: Path) -> Any:
    """Read JSON from disk and return a safe default when it fails."""
    try:
        with path.open("r", encoding="utf-8-sig") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


# TODO: Add filtering helpers for inspecting recent command history.
