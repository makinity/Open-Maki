"""Tests for settings validation and DB-only settings persistence."""

import unittest
from unittest.mock import patch

import app.services.settings_service as settings_service
from app.config import (
    DEFAULT_GROQ_LLM_MODEL,
    DEFAULT_LLM_MODEL,
    MAX_LLM_TIMEOUT_SECONDS,
    MAX_VOICE_TIMEOUT_SECONDS,
    MIN_LLM_TIMEOUT_SECONDS,
    MIN_VOICE_PHRASE_LIMIT_SECONDS,
)
from app.services.settings_service import load_settings, save_settings, validate_settings


class SettingsServiceTests(unittest.TestCase):
    """Verify settings validation for the MySQL-backed configuration."""

    def test_validate_settings_maps_legacy_voice_enabled_to_split_settings(self) -> None:
        """Legacy voice_enabled should seed both speech settings when needed."""
        settings = validate_settings({"voice_enabled": False})

        self.assertFalse(settings["speech_input_enabled"])
        self.assertFalse(settings["speech_output_enabled"])

    def test_validate_settings_clamps_speech_timeout_values(self) -> None:
        """Speech timeout settings should stay within safe bounds."""
        settings = validate_settings(
            {
                "voice_timeout_seconds": 999,
                "voice_phrase_limit_seconds": 0,
            }
        )

        self.assertEqual(settings["voice_timeout_seconds"], MAX_VOICE_TIMEOUT_SECONDS)
        self.assertEqual(
            settings["voice_phrase_limit_seconds"],
            MIN_VOICE_PHRASE_LIMIT_SECONDS,
        )

    def test_validate_settings_coerces_microphone_index(self) -> None:
        """The optional microphone index should be kept as an integer when valid."""
        settings = validate_settings({"microphone_index": "5"})

        self.assertEqual(settings["microphone_index"], 5)

    def test_validate_settings_clamps_tts_values(self) -> None:
        """TTS rate and volume should stay within safe bounds."""
        settings = validate_settings({"tts_rate": 99, "tts_volume": -1})

        self.assertEqual(settings["tts_rate"], 10)
        self.assertEqual(settings["tts_volume"], 0)

    @patch.dict(
        "os.environ",
        {"XAI_API_KEY": "test-key", "GROQ_API_KEY": "", "GROK_API_KEY": ""},
        clear=False,
    )
    def test_validate_settings_auto_enables_llm_with_xai_api_key(self) -> None:
        """LLM parsing should auto-enable when an API key is available."""
        settings = validate_settings({})

        self.assertTrue(settings["llm_parser_enabled"])
        self.assertEqual(settings["llm_model"], DEFAULT_LLM_MODEL)

    @patch.dict("os.environ", {"GROK_API_KEY": "test-key"}, clear=False)
    def test_validate_settings_auto_enables_llm_with_grok_api_key(self) -> None:
        """LLM parsing should also auto-enable for the legacy Grok env name."""
        settings = validate_settings({})

        self.assertTrue(settings["llm_parser_enabled"])
        self.assertEqual(settings["llm_model"], DEFAULT_GROQ_LLM_MODEL)

    @patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}, clear=False)
    def test_validate_settings_uses_groq_defaults_when_groq_key_is_present(self) -> None:
        """Groq-backed setups should default to a Groq-compatible model."""
        settings = validate_settings({})

        self.assertEqual(settings["llm_provider"], "auto")
        self.assertTrue(settings["llm_parser_enabled"])
        self.assertEqual(settings["llm_model"], DEFAULT_GROQ_LLM_MODEL)

    @patch.dict(
        "os.environ",
        {"XAI_API_KEY": "xai-key", "GROQ_API_KEY": "groq-key", "GROK_API_KEY": ""},
        clear=False,
    )
    def test_validate_settings_prefers_groq_when_both_provider_keys_exist(self) -> None:
        """Auto settings should resolve to a Groq-compatible model when both keys exist."""
        settings = validate_settings({})

        self.assertEqual(settings["llm_provider"], "auto")
        self.assertTrue(settings["llm_parser_enabled"])
        self.assertEqual(settings["llm_model"], DEFAULT_GROQ_LLM_MODEL)

    def test_validate_settings_clamps_llm_timeout_values(self) -> None:
        """LLM timeout settings should stay within safe bounds."""
        settings = validate_settings({"llm_timeout_seconds": 999})
        self.assertEqual(settings["llm_timeout_seconds"], MAX_LLM_TIMEOUT_SECONDS)

        settings = validate_settings({"llm_timeout_seconds": 0})
        self.assertEqual(settings["llm_timeout_seconds"], MIN_LLM_TIMEOUT_SECONDS)

    @patch.dict(
        "os.environ",
        {"XAI_API_KEY": "", "GROQ_API_KEY": "", "GROK_API_KEY": ""},
        clear=False,
    )
    def test_validate_settings_defaults_llm_model(self) -> None:
        """The default LLM model should be stable when unset."""
        settings = validate_settings({"llm_model": ""})

        self.assertEqual(settings["llm_model"], DEFAULT_LLM_MODEL)

    def test_validate_settings_rewrites_xai_model_for_groq_provider(self) -> None:
        """A Groq provider should not keep the xAI Grok model identifier."""
        settings = validate_settings(
            {
                "llm_provider": "groq",
                "llm_model": DEFAULT_LLM_MODEL,
            }
        )

        self.assertEqual(settings["llm_provider"], "groq")
        self.assertEqual(settings["llm_model"], DEFAULT_GROQ_LLM_MODEL)

    def test_validate_settings_preserves_and_cleans_wake_word_fields(self) -> None:
        """Wake-word settings should survive validation with cleaned phrase values."""
        settings = validate_settings(
            {
                "wake_word_enabled": True,
                "wake_phrases": [" hey maki ", "", "ok maki", "ok maki"],
                "custom_note": "keep me",
            }
        )

        self.assertTrue(settings["wake_word_enabled"])
        self.assertEqual(settings["wake_phrases"], ["hey maki", "ok maki"])
        self.assertEqual(settings["custom_note"], "keep me")

    @patch.object(settings_service, "save_settings_dict")
    @patch.object(settings_service, "load_settings_dict")
    @patch.object(settings_service, "ensure_database_ready")
    def test_load_settings_uses_database_only(
        self,
        mock_ensure_database_ready,
        mock_load_settings_dict,
        mock_save_settings_dict,
    ) -> None:
        """Database-backed settings should be loaded and normalized without file I/O."""
        mock_load_settings_dict.return_value = {
            "bot_name": "Maki",
            "wake_word_enabled": True,
            "wake_phrases": ["hey maki", "okay maki"],
            "tts_volume": 999,
            "custom_note": "from database",
        }

        settings = load_settings()

        self.assertTrue(settings["wake_word_enabled"])
        self.assertEqual(settings["wake_phrases"], ["hey maki", "okay maki"])
        self.assertEqual(settings["tts_volume"], 100)
        self.assertEqual(settings["custom_note"], "from database")
        mock_ensure_database_ready.assert_called_once()
        mock_save_settings_dict.assert_called_once_with(settings)

    @patch.object(settings_service, "ensure_database_ready", side_effect=RuntimeError("db down"))
    def test_load_settings_raises_when_database_is_unavailable(
        self,
        mock_ensure_database_ready,
    ) -> None:
        """Settings loading should fail fast when MySQL is unavailable."""
        with self.assertRaisesRegex(RuntimeError, "db down"):
            load_settings()

        mock_ensure_database_ready.assert_called_once()

    @patch.object(settings_service, "save_settings_dict")
    @patch.object(settings_service, "ensure_database_ready")
    def test_save_settings_writes_to_database_only(
        self,
        mock_ensure_database_ready,
        mock_save_settings_dict,
    ) -> None:
        """Saving settings should persist only through the MySQL service."""
        saved = save_settings({"bot_name": "Maki", "tts_rate": 99})

        self.assertEqual(saved["tts_rate"], 10)
        mock_ensure_database_ready.assert_called_once()
        mock_save_settings_dict.assert_called_once_with(saved)


# TODO: Add persistence tests for settings updates across multiple user profiles.
if __name__ == "__main__":
    unittest.main()
