"""MySQL-backed model helpers for command history."""

from typing import Any

from app.services.database import (
    _connect,
    _deserialize_json,
    _fetch_rows,
    _format_timestamp,
    _serialize_json,
    ensure_database_ready,
)


def load_history_entries(limit: int | None = None) -> list[dict[str, Any]]:
    """Load command history entries from MySQL in chronological order."""
    ensure_database_ready()
    params: tuple[Any, ...] = ()
    query = """
        SELECT timestamp, source, raw_text, intent, target, success, status, message, data_json
        FROM command_history
        ORDER BY id DESC
    """
    if isinstance(limit, int) and limit > 0:
        query += " LIMIT %s"
        params = (limit,)

    rows = _fetch_rows(query, params)
    history: list[dict[str, Any]] = []
    for row in reversed(rows):
        history.append(
            {
                "timestamp": _format_timestamp(row.get("timestamp")),
                "source": str(row.get("source", "")),
                "raw_text": str(row.get("raw_text", "")),
                "intent": str(row.get("intent", "")),
                "target": str(row.get("target", "")),
                "success": bool(row.get("success", False)),
                "status": str(row.get("status", "")),
                "message": str(row.get("message", "")),
                "data": _deserialize_json(row.get("data_json")),
            }
        )
    return history


def save_history_entries(entries: list[dict[str, Any]]) -> bool:
    """Replace command history rows in MySQL with the provided entries."""
    connection = _connect()
    if connection is None:
        raise RuntimeError("Could not connect to the MySQL database.")

    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM command_history")
        for entry in entries:
            cursor.execute(
                """
                INSERT INTO command_history (
                    timestamp, source, raw_text, intent, target,
                    success, status, message, data_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(entry.get("timestamp", "")),
                    str(entry.get("source", "")),
                    str(entry.get("raw_text", "")),
                    str(entry.get("intent", "")),
                    str(entry.get("target", "")),
                    bool(entry.get("success", False)),
                    str(entry.get("status", "")),
                    str(entry.get("message", "")),
                    _serialize_json(entry.get("data")),
                ),
            )
        connection.commit()
    finally:
        connection.close()

    return True


def insert_history_entry(entry: dict[str, Any]) -> bool:
    """Insert a single command history row into MySQL."""
    connection = _connect()
    if connection is None:
        raise RuntimeError("Could not connect to the MySQL database.")

    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO command_history (
                timestamp, source, raw_text, intent, target,
                success, status, message, data_json
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(entry.get("timestamp", "")),
                str(entry.get("source", "")),
                str(entry.get("raw_text", "")),
                str(entry.get("intent", "")),
                str(entry.get("target", "")),
                bool(entry.get("success", False)),
                str(entry.get("status", "")),
                str(entry.get("message", "")),
                _serialize_json(entry.get("data")),
            ),
        )
        connection.commit()
    finally:
        connection.close()

    return True
