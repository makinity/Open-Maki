"""Business logic for command history handling."""

from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import DEFAULT_HISTORY_LIMIT
from app.models.command_history import (
    insert_history_entry,
    load_history_entries,
    save_history_entries,
)
from app.services.database import ensure_database_ready


def load_history() -> list[dict[str, Any]]:
    """Load command history entries from MySQL."""
    ensure_database_ready()
    return load_history_entries()


def save_history(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Write command history entries into MySQL."""
    ensure_database_ready()
    save_history_entries(entries)
    return entries


def add_history_entry(
    command_text: str,
    intent: dict[str, Any],
    result: dict[str, Any],
    history_limit: int = DEFAULT_HISTORY_LIMIT,
    source: str = "user",
) -> dict[str, Any]:
    """Append a single history entry to the MySQL command history table."""
    ensure_database_ready()
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

    if history_limit > 0:
        history = load_history_entries(limit=history_limit)
        history.append(entry)
        save_history_entries(history[-history_limit:])
    else:
        insert_history_entry(entry)

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

