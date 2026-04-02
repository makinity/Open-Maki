"""MySQL-backed model helpers for assistant settings."""

from typing import Any

from app.config import DEFAULT_SETTINGS
from app.services.database import (
    _connect,
    _count_rows,
    _deserialize_json,
    _fetch_rows,
    _serialize_json,
    ensure_database_ready,
)


def load_settings_dict() -> dict[str, Any]:
    """Load assistant settings from the MySQL settings table."""
    ensure_database_ready()
    rows = _fetch_rows(
        """
        SELECT setting_key, setting_value
        FROM assistant_settings
        """
    )
    settings: dict[str, Any] = {}
    for row in rows:
        key = str(row.get("setting_key", "")).strip()
        if not key:
            continue
        settings[key] = _deserialize_json(row.get("setting_value"))
    return settings


def save_settings_dict(settings: dict[str, Any]) -> bool:
    """Persist assistant settings into the MySQL settings table."""
    connection = _connect()
    if connection is None:
        raise RuntimeError("Could not connect to the MySQL database.")

    try:
        cursor = connection.cursor()
        for key, value in settings.items():
            cursor.execute(
                """
                REPLACE INTO assistant_settings (setting_key, setting_value)
                VALUES (%s, %s)
                """,
                (str(key), _serialize_json(value)),
            )
        connection.commit()
    finally:
        connection.close()

    return True


def seed_default_settings(connection: Any) -> None:
    """Insert default assistant settings when the MySQL table is empty."""
    if _count_rows(connection, "assistant_settings") > 0:
        return

    cursor = connection.cursor()
    for key, value in dict(DEFAULT_SETTINGS).items():
        cursor.execute(
            """
            INSERT INTO assistant_settings (setting_key, setting_value)
            VALUES (%s, %s)
            """,
            (str(key), _serialize_json(value)),
        )
