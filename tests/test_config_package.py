"""Tests for the config package split and compatibility surface."""

import os
import unittest
from unittest.mock import patch

import app.config as app_config
import app.config.env as config_env
from app.config import (
    DEFAULT_GROQ_API_URL,
    DEFAULT_GROQ_LLM_MODEL,
    DEFAULT_LLM_MODEL,
    DEFAULT_XAI_API_URL,
    ENV_FILE,
    PUBLIC_DIR,
    database_is_enabled,
    ensure_env_loaded,
    get_database_config,
    get_database_name,
    get_env_bool,
    get_env_int,
    get_env_str,
    get_llm_api_key,
    get_llm_api_url,
    get_llm_provider,
    normalize_llm_model,
)


class ConfigPackageTests(unittest.TestCase):
    """Verify the new config package behavior and compatibility exports."""

    def setUp(self) -> None:
        """Reset the cached .env loader before each test."""
        config_env._load_env_once.cache_clear()

    @patch("app.config.env.load_dotenv")
    def test_ensure_env_loaded_calls_dotenv_once(self, mock_load_dotenv) -> None:
        """The env loader should only read the .env file once per process."""
        ensure_env_loaded()
        ensure_env_loaded()

        mock_load_dotenv.assert_called_once_with(dotenv_path=ENV_FILE, override=False)

    @patch.dict(os.environ, {"EXAMPLE_TEXT": " value ", "EXAMPLE_INT": "7", "EXAMPLE_BOOL": "yes"}, clear=False)
    def test_env_helpers_return_stripped_and_coerced_values(self) -> None:
        """Raw env helpers should normalize string, int, and bool values."""
        self.assertEqual(get_env_str("EXAMPLE_TEXT", "fallback"), "value")
        self.assertEqual(get_env_int("EXAMPLE_INT", 1), 7)
        self.assertTrue(get_env_bool("EXAMPLE_BOOL", False))

    @patch.dict(os.environ, {"XAI_API_KEY": "xai-key", "GROQ_API_KEY": "groq-key"}, clear=False)
    def test_get_llm_provider_prefers_groq_when_both_keys_exist(self) -> None:
        """Auto provider resolution should prefer Groq when both providers are configured."""
        self.assertEqual(get_llm_provider(), "groq")
        self.assertEqual(get_llm_api_key(), "groq-key")

    @patch.dict(os.environ, {"XAI_API_KEY": "", "GROK_API_KEY": "legacy-key", "GROQ_API_KEY": ""}, clear=False)
    def test_get_llm_provider_supports_legacy_grok_names(self) -> None:
        """Legacy GROK env names should still resolve through the config package."""
        self.assertEqual(get_llm_provider(), "groq")
        self.assertEqual(get_llm_api_key(), "legacy-key")
        self.assertEqual(get_llm_api_url("groq"), DEFAULT_GROQ_API_URL)

    def test_get_llm_api_url_uses_provider_defaults(self) -> None:
        """Missing provider URLs should fall back to the package defaults."""
        self.assertEqual(get_llm_api_url("xai"), DEFAULT_XAI_API_URL)
        self.assertEqual(get_llm_api_url("groq"), DEFAULT_GROQ_API_URL)

    def test_normalize_llm_model_rewrites_xai_default_for_groq(self) -> None:
        """The Groq provider should not keep the xAI default model name."""
        self.assertEqual(
            normalize_llm_model(DEFAULT_LLM_MODEL, "groq"),
            DEFAULT_GROQ_LLM_MODEL,
        )

    @patch.dict(
        os.environ,
        {
            "MAKI_DB_ENABLED": "true",
            "MAKI_DB_HOST": "db.local",
            "MAKI_DB_PORT": "3307",
            "MAKI_DB_USER": "maki",
            "MAKI_DB_PASSWORD": "secret",
            "MAKI_DB_NAME": "assistant_db",
        },
        clear=False,
    )
    def test_database_helpers_build_normalized_config(self) -> None:
        """Database config helpers should coerce env values into connection settings."""
        self.assertTrue(database_is_enabled())
        self.assertEqual(get_database_name(), "assistant_db")
        self.assertEqual(
            get_database_config(),
            {
                "host": "db.local",
                "port": 3307,
                "user": "maki",
                "password": "secret",
                "autocommit": False,
                "database": "assistant_db",
            },
        )
        self.assertEqual(
            get_database_config(include_database=False),
            {
                "host": "db.local",
                "port": 3307,
                "user": "maki",
                "password": "secret",
                "autocommit": False,
            },
        )

    def test_app_config_reexports_runtime_symbols(self) -> None:
        """The config package should preserve the old import surface for runtime symbols."""
        self.assertEqual(app_config.BOT_NAME, "Maki")
        self.assertTrue(callable(app_config.get_llm_api_url))
        self.assertTrue(callable(app_config.get_database_config))
        self.assertEqual(app_config.PUBLIC_DIR, PUBLIC_DIR)


if __name__ == "__main__":
    unittest.main()
