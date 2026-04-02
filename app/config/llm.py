"""LLM configuration helpers and defaults."""

from typing import Literal

from app.config.env import get_env_str

DEFAULT_XAI_API_URL = "https://api.x.ai/v1"
DEFAULT_GROQ_API_URL = "https://api.groq.com/openai/v1"
DEFAULT_LLM_MODEL = "grok-4.20-reasoning"
FAST_LLM_MODEL = "grok-3-mini-fast"
DEFAULT_GROQ_LLM_MODEL = "openai/gpt-oss-20b"

LLM_PROVIDER_VALUES = ("auto", "xai", "groq")
XAI_API_KEY_ENV_NAMES = ("XAI_API_KEY",)
XAI_API_URL_ENV_NAMES = ("XAI_API_URL",)
GROQ_API_KEY_ENV_NAMES = ("GROQ_API_KEY", "GROK_API_KEY")
GROQ_API_URL_ENV_NAMES = ("GROQ_API_URL", "GROK_API_URL")


def get_llm_provider(preferred_provider: str | None = None) -> Literal["xai", "groq", ""]:
    """Return the active LLM provider based on settings or available keys."""
    normalized_provider = str(preferred_provider or "").strip().lower()
    if normalized_provider == "xai":
        return "xai"
    if normalized_provider == "groq":
        return "groq"

    if _has_any_env_value(XAI_API_KEY_ENV_NAMES):
        return "xai"
    if _has_any_env_value(GROQ_API_KEY_ENV_NAMES):
        return "groq"
    return ""


def get_llm_api_key(preferred_provider: str | None = None) -> str:
    """Return the configured API key for the active LLM provider."""
    provider = get_llm_provider(preferred_provider)
    if provider == "groq":
        return _first_env_value(GROQ_API_KEY_ENV_NAMES)
    if provider == "xai":
        return _first_env_value(XAI_API_KEY_ENV_NAMES)
    return ""


def get_llm_api_url(preferred_provider: str | None = None) -> str:
    """Return the configured base URL for the active LLM provider."""
    provider = get_llm_provider(preferred_provider)
    if provider == "groq":
        return _first_env_value(GROQ_API_URL_ENV_NAMES) or DEFAULT_GROQ_API_URL
    if provider == "xai":
        return _first_env_value(XAI_API_URL_ENV_NAMES) or DEFAULT_XAI_API_URL
    return DEFAULT_XAI_API_URL


def get_default_llm_model(preferred_provider: str | None = None) -> str:
    """Return the default model for the active LLM provider."""
    provider = get_llm_provider(preferred_provider)
    if provider == "groq":
        return DEFAULT_GROQ_LLM_MODEL
    return DEFAULT_LLM_MODEL


def normalize_llm_model(model_name: str, preferred_provider: str | None = None) -> str:
    """Return a provider-compatible model name with a safe default."""
    cleaned_model = " ".join(str(model_name).split()).strip()
    default_model = get_default_llm_model(preferred_provider)
    provider = get_llm_provider(preferred_provider)

    if not cleaned_model:
        return default_model

    if provider == "groq" and cleaned_model in {DEFAULT_LLM_MODEL, FAST_LLM_MODEL}:
        return default_model

    return cleaned_model


def get_xai_api_key() -> str:
    """Return the configured xAI API key from supported environment names."""
    return get_llm_api_key("xai")


def get_xai_api_url() -> str:
    """Return the configured xAI base URL from supported environment names."""
    return get_llm_api_url("xai")


def _first_env_value(env_names: tuple[str, ...]) -> str:
    """Return the first non-empty environment value from a list of names."""
    for env_name in env_names:
        value = get_env_str(env_name, "")
        if value:
            return value
    return ""


def _has_any_env_value(env_names: tuple[str, ...]) -> bool:
    """Return True when any of the provided environment names is configured."""
    return bool(_first_env_value(env_names))
