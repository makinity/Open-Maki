"""Environment loading and raw env reader helpers."""

from functools import lru_cache
import os

from dotenv import load_dotenv

from app.config.paths import ENV_FILE


@lru_cache(maxsize=1)
def _load_env_once() -> None:
    """Load the local .env file one time for the current process."""
    load_dotenv(dotenv_path=ENV_FILE, override=False)


def ensure_env_loaded() -> None:
    """Ensure the local .env file has been loaded into the process environment."""
    _load_env_once()


def get_env_str(name: str, default: str = "") -> str:
    """Return one environment variable as a stripped string."""
    ensure_env_loaded()
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip()


def get_env_int(name: str, default: int) -> int:
    """Return one environment variable as an integer with a fallback."""
    ensure_env_loaded()
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def get_env_bool(name: str, default: bool) -> bool:
    """Return one environment variable as a boolean with a fallback."""
    ensure_env_loaded()
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
