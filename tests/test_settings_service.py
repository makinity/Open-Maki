"""Tests for settings validation and speech setting compatibility."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import app.services.settings_service as settings_service
from app.config import MAX_VOICE_TIMEOUT_SECONDS, MIN_VOICE_PHRASE_LIMIT_SECONDS
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

            with patch.object(settings_service, "SETTINGS_FILE", settings_path):
                loaded_settings = settings_service.load_settings()

            saved_settings = json.loads(settings_path.read_text(encoding="utf-8"))
            self.assertTrue(loaded_settings["wake_word_enabled"])
            self.assertEqual(loaded_settings["wake_phrases"], original_settings["wake_phrases"])
            self.assertEqual(saved_settings["wake_phrases"], original_settings["wake_phrases"])
            self.assertEqual(saved_settings["custom_note"], "preserve me")


# TODO: Add persistence tests for settings updates across multiple user profiles.
if __name__ == "__main__":
    unittest.main()
