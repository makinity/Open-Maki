"""MySQL-backed model helpers for application aliases."""

from typing import Any

from app.services.database import (
    _count_rows,
    _deserialize_json,
    _fetch_rows,
    _serialize_json,
    ensure_database_ready,
)

BUILTIN_APP_ENTRIES: list[dict[str, object]] = [
    {"name": "calculator", "aliases": ["calculator", "calc"], "command": ["calc"]},
    {"name": "notepad", "aliases": ["notepad"], "command": ["notepad"]},
    {"name": "paint", "aliases": ["paint"], "command": ["mspaint"]},
    {"name": "powershell", "aliases": ["powershell"], "command": ["powershell"]},
    {"name": "command prompt", "aliases": ["command prompt", "cmd"], "command": ["cmd"]},
    {"name": "file explorer", "aliases": ["file explorer", "explorer"], "command": ["explorer"]},
    {"name": "chrome", "aliases": ["chrome", "google chrome"], "command": ["chrome"]},
    {"name": "edge", "aliases": ["edge", "microsoft edge"], "command": ["msedge"]},
    {"name": "vscode", "aliases": ["vscode", "visual studio code", "code"], "command": ["code"]},
]


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
                "command": _normalize_command(_deserialize_json(row.get("command_json"))),
            }
        )
    return entries


def seed_builtin_app_aliases(connection: Any) -> None:
    """Seed app aliases from built-in defaults when the table is empty."""
    if _count_rows(connection, "app_aliases") > 0:
        return

    for entry in BUILTIN_APP_ENTRIES:
        insert_app_alias_entry(
            connection,
            name=str(entry.get("name", "")),
            command=entry.get("command"),
            aliases=entry.get("aliases", []),
        )


def insert_app_alias_entry(connection: Any, name: str, command: Any, aliases: Any) -> None:
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


def _normalize_command(command: Any) -> list[str] | str | None:
    """Normalize app commands into the forms supported by the launcher."""
    if isinstance(command, str):
        cleaned_command = command.strip()
        return cleaned_command or None

    if isinstance(command, (list, tuple)):
        parts = [str(part).strip() for part in command if str(part).strip()]
        return parts or None

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
