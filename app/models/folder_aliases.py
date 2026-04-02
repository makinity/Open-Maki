"""MySQL-backed model helpers for folder aliases."""

from pathlib import Path
from typing import Any

from app.config import HOME_DIR
from app.services.database import _count_rows, _fetch_rows, ensure_database_ready

BUILTIN_FOLDER_ENTRIES: list[dict[str, object]] = [
    {"name": "desktop", "aliases": ["desktop"], "path": HOME_DIR / "Desktop"},
    {"name": "documents", "aliases": ["documents", "document"], "path": HOME_DIR / "Documents"},
    {"name": "downloads", "aliases": ["downloads", "download"], "path": HOME_DIR / "Downloads"},
    {"name": "pictures", "aliases": ["pictures", "picture"], "path": HOME_DIR / "Pictures"},
]


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


def seed_builtin_folder_aliases(connection: Any) -> None:
    """Seed folder aliases from built-in defaults when the table is empty."""
    if _count_rows(connection, "folder_aliases") > 0:
        return

    for entry in BUILTIN_FOLDER_ENTRIES:
        insert_folder_alias_entry(
            connection,
            name=str(entry.get("name", "")),
            path=entry.get("path"),
            aliases=entry.get("aliases", []),
        )


def insert_folder_alias_entry(connection: Any, name: str, path: Any, aliases: Any) -> None:
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
