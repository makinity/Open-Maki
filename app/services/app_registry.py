"""Service helpers for loading and resolving app and folder aliases."""

from pathlib import Path
from typing import Any

from app.services.database import (
    ensure_database_ready,
    load_app_alias_entries,
    load_folder_alias_entries,
)
from app.utils.helpers import normalize_text

RegistryType = dict[str, dict[str, dict[str, Any]]]


def load_app_registry() -> RegistryType:
    """Load application and folder aliases from MySQL."""
    ensure_database_ready()
    registry = _create_empty_registry()

    for entry in load_app_alias_entries():
        _register_application(
            registry,
            name=str(entry.get("name", "")),
            command=entry.get("command"),
            aliases=[str(entry.get("alias", ""))],
        )

    for entry in load_folder_alias_entries():
        _register_folder(
            registry,
            name=str(entry.get("name", "")),
            path=entry.get("path"),
            aliases=[str(entry.get("alias", ""))],
        )

    return registry


def resolve_app_entry(
    app_name: str,
    registry: RegistryType | None = None,
) -> dict[str, Any] | None:
    """Resolve an application alias into a registry entry."""
    normalized_name = normalize_alias(app_name)
    if not normalized_name:
        return None

    registry = registry or _create_empty_registry()
    return registry.get("apps", {}).get(normalized_name)


def resolve_folder_path(
    folder_name: str,
    registry: RegistryType | None = None,
) -> Path | None:
    """Resolve a folder alias into a concrete path."""
    normalized_name = normalize_alias(folder_name)
    if not normalized_name:
        return None

    registry = registry or _create_empty_registry()
    folder_entry = registry.get("folders", {}).get(normalized_name)
    if not isinstance(folder_entry, dict):
        return None

    raw_path = folder_entry.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None

    return Path(raw_path)


def normalize_alias(name: str) -> str:
    """Normalize an alias for consistent registry lookups."""
    return normalize_text(name).lower()


def _create_empty_registry() -> RegistryType:
    """Return an empty registry structure for apps and folders."""
    return {
        "apps": {},
        "folders": {},
    }


def _register_application(
    registry: RegistryType,
    name: str,
    command: Any,
    aliases: Any,
) -> None:
    """Register an application entry under all supported aliases."""
    normalized_name = normalize_alias(name)
    normalized_command = _normalize_command(command)
    normalized_aliases = _extract_aliases(aliases)

    if not normalized_name or normalized_command is None:
        return

    entry = {
        "name": name.strip() or normalized_name,
        "command": normalized_command,
    }

    for alias in {normalized_name, *normalized_aliases}:
        registry["apps"][alias] = entry


def _register_folder(
    registry: RegistryType,
    name: str,
    path: Any,
    aliases: Any,
) -> None:
    """Register a folder entry under all supported aliases."""
    normalized_name = normalize_alias(name)
    normalized_path = _normalize_path(path)
    normalized_aliases = _extract_aliases(aliases)

    if not normalized_name or normalized_path is None:
        return

    entry = {
        "name": name.strip() or normalized_name,
        "path": str(normalized_path),
    }

    for alias in {normalized_name, *normalized_aliases}:
        registry["folders"][alias] = entry


def _extract_aliases(raw_aliases: Any) -> set[str]:
    """Return normalized aliases from registry entry data."""
    if isinstance(raw_aliases, str):
        raw_values = [raw_aliases]
    elif isinstance(raw_aliases, (list, tuple, set)):
        raw_values = list(raw_aliases)
    else:
        raw_values = []

    normalized_aliases: set[str] = set()
    for alias in raw_values:
        if not isinstance(alias, str):
            continue

        normalized_alias = normalize_alias(alias)
        if normalized_alias:
            normalized_aliases.add(normalized_alias)

    return normalized_aliases


def _normalize_command(command: Any) -> list[str] | str | None:
    """Normalize a command value into a safe app launch structure."""
    if isinstance(command, str):
        cleaned_command = command.strip()
        return cleaned_command or None

    if isinstance(command, (list, tuple)):
        parts = [str(part).strip() for part in command if str(part).strip()]
        return parts or None

    return None


def _normalize_path(path: Any) -> Path | None:
    """Normalize a path-like value into a Path object."""
    if isinstance(path, Path):
        return path

    if isinstance(path, str) and path.strip():
        return Path(path.strip())

    return None


# TODO: Add helpers for writing app and folder aliases back to MySQL tables.
