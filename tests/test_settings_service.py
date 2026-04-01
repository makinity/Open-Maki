"""Tests for settings validation and speech setting compatibility."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
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
from app.services.settings_service import validate_settings


class SettingsServiceTests(unittest.TestCase):
    """Verify settings validation for the Phase 4 speech configuration."""

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

    @patch.dict("os.environ", {"XAI_API_KEY": "test-key"}, clear=False)
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

    def test_load_settings_does_not_erase_wake_phrases_from_disk(self) -> None:
        """Loading settings should not strip wake-word fields during normalization."""
        with TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            original_settings = {
                "bot_name": "Maki",
                "speech_input_enabled": True,
                "speech_output_enabled": True,
                "wake_word_enabled": True,
                "wake_phrases": ["hey maki", "okay maki"],
                "custom_note": "preserve me",
            }
            settings_path.write_text(json.dumps(original_settings), encoding="utf-8")

            with patch.object(settings_service, "SETTINGS_FILE", settings_path), patch.object(
                settings_service,
                "database_is_ready",
                return_value=False,
            ):
                loaded_settings = settings_service.load_settings()

            saved_settings = json.loads(settings_path.read_text(encoding="utf-8"))
            self.assertTrue(loaded_settings["wake_word_enabled"])
            self.assertEqual(loaded_settings["wake_phrases"], original_settings["wake_phrases"])
            self.assertEqual(saved_settings["wake_phrases"], original_settings["wake_phrases"])
            self.assertEqual(saved_settings["custom_note"], "preserve me")

    @patch.object(settings_service, "save_settings_dict")
    @patch.object(settings_service, "load_settings_dict")
    @patch.object(settings_service, "database_is_ready", return_value=True)
    def test_load_settings_uses_database_when_available(
        self,
        mock_database_is_ready,
        mock_load_settings_dict,
        mock_save_settings_dict,
    ) -> None:
        """Database-backed settings should be loaded without touching the JSON file."""
        mock_load_settings_dict.return_value = {
            "bot_name": "Maki",
            "wake_word_enabled": True,
            "wake_phrases": ["hey maki", "okay maki"],
            "custom_note": "from database",
        }

        settings = settings_service.load_settings()

        self.assertTrue(settings["wake_word_enabled"])
        self.assertEqual(settings["wake_phrases"], ["hey maki", "okay maki"])
        self.assertEqual(settings["custom_note"], "from database")
        mock_database_is_ready.assert_called()
        mock_save_settings_dict.assert_called_once()


# TODO: Add persistence tests for settings updates across multiple user profiles.
if __name__ == "__main__":
    unittest.main()
