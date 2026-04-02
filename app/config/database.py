"""Database configuration helpers and defaults."""

from typing import Any

from app.config.env import get_env_bool, get_env_int, get_env_str

DEFAULT_DB_HOST = "127.0.0.1"
DEFAULT_DB_PORT = 3306
DEFAULT_DB_USER = "root"
DEFAULT_DB_NAME = "maki_assistant"


def database_is_enabled() -> bool:
    """Return True when the database backend is enabled via environment."""
    return get_env_bool("MAKI_DB_ENABLED", False)


def get_database_name() -> str:
    """Return the configured database name."""
    return get_env_str("MAKI_DB_NAME", DEFAULT_DB_NAME)


def get_database_config(include_database: bool = True) -> dict[str, Any]:
    """Return the normalized database connection configuration."""
    connection_config: dict[str, Any] = {
        "host": get_env_str("MAKI_DB_HOST", DEFAULT_DB_HOST),
        "port": get_env_int("MAKI_DB_PORT", DEFAULT_DB_PORT),
        "user": get_env_str("MAKI_DB_USER", DEFAULT_DB_USER),
        "password": get_env_str("MAKI_DB_PASSWORD", ""),
        "autocommit": False,
    }
    if include_database:
        connection_config["database"] = get_database_name()
    return connection_config
