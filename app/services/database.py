"""Database helpers for MySQL-backed assistant storage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import (
    DEFAULT_SETTINGS,
    database_is_enabled,
    get_database_config,
    get_database_name,
)

try:
    import mysql.connector as mysql_connector
except Exception:  # pragma: no cover - optional dependency
    mysql_connector = None

_DATABASE_INITIALIZED = False
_DATABASE_READY = False
_DATABASE_ERROR = ""


def initialize_database(logger: Any | None = None) -> bool:
    """Create the configured MySQL schema and seed default assistant data."""
    global _DATABASE_INITIALIZED, _DATABASE_READY, _DATABASE_ERROR

    if _DATABASE_INITIALIZED:
        return _DATABASE_READY

    _DATABASE_INITIALIZED = True
    if not _database_requested():
        _DATABASE_ERROR = (
            "MySQL storage is required. Set MAKI_DB_ENABLED=true and provide the "
            "database connection settings in .env."
        )
        _DATABASE_READY = False
        return False

    if mysql_connector is None:
        _DATABASE_ERROR = (
            "MySQL storage is required, but mysql-connector-python is not installed."
        )
        _DATABASE_READY = False
        return False

    try:
        _ensure_database_exists()
        connection = _connect()
        if connection is None:
            _DATABASE_ERROR = "Could not connect to the configured MySQL database."
            _DATABASE_READY = False
            return False

        try:
            _ensure_tables(connection)
            _ensure_optional_columns(connection)
            _seed_settings_table(connection)
            _seed_command_patterns_table(connection)
            _seed_website_aliases_table(connection)
            _seed_app_alias_tables(connection)
            connection.commit()
            _DATABASE_ERROR = ""
            _DATABASE_READY = True
        finally:
            connection.close()
    except Exception as error:  # pragma: no cover - depends on external MySQL state
        _DATABASE_READY = False
        _DATABASE_ERROR = f"MySQL storage is unavailable: {error}"
        if logger is not None:
            logger.error("%s", _DATABASE_ERROR)

    return _DATABASE_READY


def database_is_ready() -> bool:
    """Return True when the configured MySQL backend is available."""
    return initialize_database()


def ensure_database_ready() -> None:
    """Raise an error when the required MySQL backend is unavailable."""
    if initialize_database():
        return

    raise RuntimeError(
        _DATABASE_ERROR or "MySQL storage is required but could not be initialized."
    )


def get_database_error() -> str:
    """Return the last known database initialization error message."""
    initialize_database()
    return _DATABASE_ERROR


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


def load_command_patterns() -> list[dict[str, Any]]:
    """Load enabled command templates from the MySQL command pattern table."""
    ensure_database_ready()
    rows = _fetch_rows(
        """
        SELECT phrase_template, intent, fixed_target, priority
        FROM command_patterns
        WHERE enabled = 1
        ORDER BY priority ASC, CHAR_LENGTH(phrase_template) DESC
        """
    )
    patterns: list[dict[str, Any]] = []
    for row in rows:
        template = str(row.get("phrase_template", "")).strip()
        intent = str(row.get("intent", "")).strip()
        if not template or not intent:
            continue

        patterns.append(
            {
                "phrase_template": template,
                "intent": intent,
                "fixed_target": str(row.get("fixed_target") or "").strip(),
                "priority": int(row.get("priority") or 100),
            }
        )
    return patterns


def load_website_aliases() -> dict[str, dict[str, str]]:
    """Load enabled website aliases from MySQL."""
    ensure_database_ready()
    rows = _fetch_rows(
        """
        SELECT alias, display_name, url, search_url_template
        FROM website_aliases
        WHERE enabled = 1
        """
    )
    aliases: dict[str, dict[str, str]] = {}
    for row in rows:
        alias = str(row.get("alias", "")).strip().lower()
        url = str(row.get("url") or "").strip()
        if not alias or not url:
            continue

        aliases[alias] = {
            "name": str(row.get("display_name", alias)).strip() or alias.title(),
            "url": url,
            "search_url_template": str(row.get("search_url_template") or "").strip(),
        }
    return aliases


def load_app_alias_entries() -> list[dict[str, Any]]:
    """Load enabled app alias rows from MySQL."""
    ensure_database_ready()
    rows = _fetch_rows(
        """
        SELECT alias, name, command_json
        FROM app_aliases
        WHERE enabled = 1
        """
    )
    entries: list[dict[str, Any]] = []
    for row in rows:
        alias = str(row.get("alias", "")).strip().lower()
        if not alias:
            continue

        entries.append(
            {
                "alias": alias,
                "name": str(row.get("name", alias)).strip() or alias,
                "command": _deserialize_json(row.get("command_json")),
            }
        )
    return entries


def load_folder_alias_entries() -> list[dict[str, Any]]:
    """Load enabled folder alias rows from MySQL."""
    ensure_database_ready()
    rows = _fetch_rows(
        """
        SELECT alias, name, path
        FROM folder_aliases
        WHERE enabled = 1
        """
    )
    entries: list[dict[str, Any]] = []
    for row in rows:
        alias = str(row.get("alias", "")).strip().lower()
        path = str(row.get("path", "")).strip()
        if not alias or not path:
            continue

        entries.append(
            {
                "alias": alias,
                "name": str(row.get("name", alias)).strip() or alias,
                "path": path,
            }
        )
    return entries


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


def _database_requested() -> bool:
    """Return True when MySQL storage has been enabled through the environment."""
    return database_is_enabled()


def _connect(include_database: bool = True) -> Any | None:
    """Return a new MySQL connection when the driver and configuration are available."""
    if mysql_connector is None:
        return None

    connection_config = get_database_config(include_database=include_database)

    try:  # pragma: no cover - depends on external MySQL state
        return mysql_connector.connect(**connection_config)
    except Exception:
        return None


def _ensure_database_exists() -> None:
    """Create the configured MySQL database when it does not yet exist."""
    connection = _connect(include_database=False)
    if connection is None:
        raise RuntimeError("Could not connect to the MySQL server.")

    database_name = get_database_name()
    try:  # pragma: no cover - depends on external MySQL state
        cursor = connection.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database_name}`")
        connection.commit()
    finally:
        connection.close()


def _ensure_tables(connection: Any) -> None:
    """Create the assistant tables required by the MySQL backend."""
    cursor = connection.cursor()
    statements = [
        """
        CREATE TABLE IF NOT EXISTS assistant_settings (
            setting_key VARCHAR(100) PRIMARY KEY,
            setting_value LONGTEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS command_patterns (
            id INT AUTO_INCREMENT PRIMARY KEY,
            phrase_template VARCHAR(255) NOT NULL UNIQUE,
            intent VARCHAR(100) NOT NULL,
            fixed_target TEXT NULL,
            priority INT NOT NULL DEFAULT 100,
            enabled BOOLEAN NOT NULL DEFAULT TRUE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS website_aliases (
            alias VARCHAR(100) PRIMARY KEY,
            display_name VARCHAR(100) NOT NULL,
            url TEXT NOT NULL,
            search_url_template TEXT NULL,
            enabled BOOLEAN NOT NULL DEFAULT TRUE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS app_aliases (
            alias VARCHAR(100) PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            command_json LONGTEXT NOT NULL,
            enabled BOOLEAN NOT NULL DEFAULT TRUE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS folder_aliases (
            alias VARCHAR(100) PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            path TEXT NOT NULL,
            enabled BOOLEAN NOT NULL DEFAULT TRUE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS command_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            timestamp DATETIME NOT NULL,
            source VARCHAR(20) NOT NULL,
            raw_text TEXT NOT NULL,
            intent VARCHAR(100) NOT NULL,
            target TEXT NOT NULL,
            success BOOLEAN NOT NULL,
            status VARCHAR(50) NOT NULL,
            message TEXT NOT NULL,
            data_json LONGTEXT NULL
        )
        """,
    ]
    for statement in statements:
        cursor.execute(statement)


def _seed_settings_table(connection: Any) -> None:
    """Insert default assistant settings when the MySQL settings table is empty."""
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


def _seed_command_patterns_table(connection: Any) -> None:
    """Insert any missing default command templates into the database."""
    from app.models.command_patterns import DEFAULT_COMMAND_PATTERNS

    cursor = connection.cursor()
    for pattern in DEFAULT_COMMAND_PATTERNS:
        cursor.execute(
            """
            INSERT IGNORE INTO command_patterns (phrase_template, intent, fixed_target, priority, enabled)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                str(pattern.get("phrase_template", "")),
                str(pattern.get("intent", "")),
                str(pattern.get("fixed_target", "")),
                int(pattern.get("priority", 100)),
                True,
            ),
        )


def _seed_website_aliases_table(connection: Any) -> None:
    """Insert missing website aliases and backfill default search templates."""
    from app.models.website_aliases import DEFAULT_WEBSITE_ENTRIES

    cursor = connection.cursor()
    for entry in DEFAULT_WEBSITE_ENTRIES:
        cursor.execute(
            """
            INSERT IGNORE INTO website_aliases (alias, display_name, url, search_url_template, enabled)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                str(entry.get("alias", "")).lower(),
                str(entry.get("name", "")),
                str(entry.get("url", "")),
                str(entry.get("search_url_template", "")),
                True,
            ),
        )
        search_url_template = str(entry.get("search_url_template", "")).strip()
        if search_url_template:
            cursor.execute(
                """
                UPDATE website_aliases
                SET search_url_template = %s
                WHERE alias = %s AND (search_url_template IS NULL OR search_url_template = '')
                """,
                (search_url_template, str(entry.get("alias", "")).lower()),
            )


def _ensure_optional_columns(connection: Any) -> None:
    """Add newer optional columns to existing tables when they are missing."""
    _ensure_column(
        connection,
        table_name="website_aliases",
        column_name="search_url_template",
        definition="TEXT NULL",
    )


def _ensure_column(
    connection: Any,
    table_name: str,
    column_name: str,
    definition: str,
) -> None:
    """Add one column to an existing table when it is missing."""
    if _column_exists(connection, table_name, column_name):
        return

    cursor = connection.cursor()
    cursor.execute(
        f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"
    )


def _column_exists(connection: Any, table_name: str, column_name: str) -> bool:
    """Return True when one column already exists in the active database."""
    database_name = get_database_name()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s AND column_name = %s
        """,
        (database_name, table_name, column_name),
    )
    row = cursor.fetchone()
    return bool(row and int(row[0]) > 0)


def _seed_app_alias_tables(connection: Any) -> None:
    """Seed app and folder aliases from built-in defaults."""
    from app.models.app_aliases import BUILTIN_APP_ENTRIES
    from app.models.folder_aliases import BUILTIN_FOLDER_ENTRIES

    if _count_rows(connection, "app_aliases") == 0:
        for entry in BUILTIN_APP_ENTRIES:
            _insert_app_alias_entry(
                connection,
                name=str(entry.get("name", "")),
                command=entry.get("command"),
                aliases=entry.get("aliases", []),
            )

    if _count_rows(connection, "folder_aliases") == 0:
        for entry in BUILTIN_FOLDER_ENTRIES:
            _insert_folder_alias_entry(
                connection,
                name=str(entry.get("name", "")),
                path=entry.get("path"),
                aliases=entry.get("aliases", []),
            )


def _insert_app_alias_entry(connection: Any, name: str, command: Any, aliases: Any) -> None:
    """Insert or replace one app alias entry across all of its aliases."""
    normalized_name = str(name).strip()
    normalized_command = _normalize_command(command)
    if not normalized_name or normalized_command is None:
        return

    cursor = connection.cursor()
    alias_values = _extract_aliases([normalized_name, *list(_extract_aliases(aliases))])
    for alias in alias_values:
        cursor.execute(
            """
            REPLACE INTO app_aliases (alias, name, command_json, enabled)
            VALUES (%s, %s, %s, %s)
            """,
            (
                alias,
                normalized_name,
                _serialize_json(normalized_command),
                True,
            ),
        )


def _insert_folder_alias_entry(connection: Any, name: str, path: Any, aliases: Any) -> None:
    """Insert or replace one folder alias entry across all of its aliases."""
    normalized_name = str(name).strip()
    normalized_path = _normalize_path(path)
    if not normalized_name or normalized_path is None:
        return

    cursor = connection.cursor()
    alias_values = _extract_aliases([normalized_name, *list(_extract_aliases(aliases))])
    for alias in alias_values:
        cursor.execute(
            """
            REPLACE INTO folder_aliases (alias, name, path, enabled)
            VALUES (%s, %s, %s, %s)
            """,
            (
                alias,
                normalized_name,
                str(normalized_path),
                True,
            ),
        )


def _count_rows(connection: Any, table_name: str) -> int:
    """Return the number of rows currently stored inside one table."""
    cursor = connection.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    row = cursor.fetchone()
    return int(row[0] if row else 0)


def _fetch_rows(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    """Return query rows as dictionaries from the configured MySQL database."""
    connection = _connect()
    if connection is None:
        raise RuntimeError("Could not connect to the MySQL database.")

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params)
        return list(cursor.fetchall())
    except Exception as error:
        raise RuntimeError(f"MySQL query failed: {error}") from error
    finally:
        connection.close()


def _serialize_json(value: Any) -> str:
    """Serialize Python data into JSON text for MySQL storage."""
    return json.dumps(value)


def _deserialize_json(value: Any) -> Any:
    """Deserialize JSON text from MySQL into Python data."""
    if value is None:
        return None

    if not isinstance(value, str):
        return value

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _format_timestamp(value: Any) -> str:
    """Return a stable string value for history timestamps."""
    if value is None:
        return ""

    if hasattr(value, "isoformat"):
        return value.isoformat(timespec="seconds")

    return str(value)


def _normalize_command(command: Any) -> list[str] | str | None:
    """Normalize app commands into the forms supported by the launcher."""
    if isinstance(command, str):
        cleaned_command = command.strip()
        return cleaned_command or None

    if isinstance(command, (list, tuple)):
        parts = [str(part).strip() for part in command if str(part).strip()]
        return parts or None

    return None


def _normalize_path(path: Any) -> Path | None:
    """Normalize folder paths into a Path object."""
    if isinstance(path, Path):
        return path

    if isinstance(path, str) and path.strip():
        return Path(path.strip())

    return None


def _extract_aliases(raw_aliases: Any) -> set[str]:
    """Return normalized alias strings from raw config data."""
    if isinstance(raw_aliases, str):
        raw_values = [raw_aliases]
    elif isinstance(raw_aliases, (list, tuple, set)):
        raw_values = list(raw_aliases)
    else:
        raw_values = []

    aliases: set[str] = set()
    for item in raw_values:
        if not isinstance(item, str):
            continue

        alias = " ".join(item.strip().lower().split())
        if alias:
            aliases.add(alias)
    return aliases


# TODO: Add helper functions for updating command tables from an admin interface.
