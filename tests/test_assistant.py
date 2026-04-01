"""Tests for assistant speech integration and history source tracking."""

import unittest
from unittest.mock import patch

from app.assistant import MakiBotAssistant

_TEST_SETTINGS = {
    "bot_name": "Maki",
    "speech_input_enabled": True,
    "speech_output_enabled": False,
    "voice_timeout_seconds": 5,
    "voice_phrase_limit_seconds": 8,
    "wake_word_enabled": False,
    "wake_phrases": ["hey maki"],
    "require_confirmation": True,
    "console_fallback_enabled": True,
    "typing_live_mode": False,
    "history_limit": 10,
    "allow_system_commands": False,
    "open_browser_enabled": True,
    "llm_parser_enabled": True,
    "llm_model": "grok-4.20-reasoning",
    "llm_timeout_seconds": 15,
}


class AssistantSpeechIntegrationTests(unittest.TestCase):
    """Verify assistant handling of the speech payload format."""

    @patch("app.assistant.load_app_registry", return_value={"apps": {}, "folders": {}})
    @patch("app.assistant.add_history_entry")
    @patch("app.assistant.speak")
    @patch("app.assistant.route_command")
    @patch("app.assistant.listen")
    def test_run_records_voice_source_in_history(
        self,
        mock_listen,
        mock_route_command,
        mock_speak,
        mock_add_history_entry,
        mock_load_app_registry,
    ) -> None:
        """A recognized voice command should be saved with source='voice'."""
        mock_listen.return_value = {
            "text": "open chrome",
            "source": "voice",
            "used_fallback": False,
            "status": "ok",
        }
        mock_route_command.return_value = {
            "success": True,
            "message": "Stopping now.",
            "data": {"should_exit": True},
        }

        assistant = MakiBotAssistant(settings=dict(_TEST_SETTINGS))
        assistant.run()

        self.assertEqual(mock_add_history_entry.call_args.kwargs["source"], "voice")
        self.assertGreaterEqual(mock_speak.call_count, 2)
        mock_load_app_registry.assert_called_once()

    @patch("app.assistant.load_app_registry", return_value={"apps": {}, "folders": {}})
    @patch("app.assistant.add_history_entry")
    @patch("app.assistant.speak")
    @patch("app.assistant.route_command")
    @patch("app.assistant.listen")
    def test_run_records_console_source_after_fallback(
        self,
        mock_listen,
        mock_route_command,
        mock_speak,
        mock_add_history_entry,
        mock_load_app_registry,
    ) -> None:
        """A console fallback command should be saved with source='console'."""
        mock_listen.return_value = {
            "text": "help",
            "source": "console",
            "used_fallback": True,
            "status": "ok",
        }
        mock_route_command.return_value = {
            "success": True,
            "message": "Stopping now.",
            "data": {"should_exit": True},
        }

        assistant = MakiBotAssistant(settings=dict(_TEST_SETTINGS))
        assistant.run()

        self.assertEqual(mock_add_history_entry.call_args.kwargs["source"], "console")
        self.assertGreaterEqual(mock_speak.call_count, 2)
        mock_load_app_registry.assert_called_once()

    @patch("app.assistant.load_app_registry", return_value={"apps": {}, "folders": {}})
    @patch("app.assistant.add_history_entry")
    @patch("app.assistant.speak")
    @patch("app.assistant.route_command")
    @patch("app.assistant.listen")
    def test_run_accepts_a_follow_up_command_after_wake_word_only(
        self,
        mock_listen,
        mock_route_command,
        mock_speak,
        mock_add_history_entry,
        mock_load_app_registry,
    ) -> None:
        """A bare wake phrase should arm the next listen turn without repeating it."""
        mock_listen.side_effect = [
            {
                "text": "",
                "source": "console",
                "used_fallback": False,
                "status": "wake_word_only",
            },
            {
                "text": "open chrome",
                "source": "console",
                "used_fallback": False,
                "status": "ok",
            },
        ]
        mock_route_command.return_value = {
            "success": True,
            "message": "Stopping now.",
            "data": {"should_exit": True},
        }

        assistant = MakiBotAssistant(
            settings={**_TEST_SETTINGS, "wake_word_enabled": True}
        )
        assistant.run()

        spoken_messages = [call.args[0] for call in mock_speak.call_args_list]
        self.assertEqual(spoken_messages[1], "I'm listening.")
        self.assertEqual(mock_route_command.call_count, 1)
        self.assertEqual(mock_add_history_entry.call_count, 1)
        self.assertTrue(mock_listen.call_args_list[0].kwargs["settings"]["wake_word_enabled"])
        self.assertFalse(mock_listen.call_args_list[1].kwargs["settings"]["wake_word_enabled"])
        mock_load_app_registry.assert_called_once()

    @patch("app.assistant.load_app_registry", return_value={"apps": {}, "folders": {}})
    @patch("app.assistant.add_history_entry")
    @patch("app.assistant.speak")
    @patch("app.assistant.route_command")
    @patch("app.assistant.listen")
    def test_run_ignores_unrecognized_voice_noise_while_waiting_for_wake_word(
        self,
        mock_listen,
        mock_route_command,
        mock_speak,
        mock_add_history_entry,
        mock_load_app_registry,
    ) -> None:
        """Background noise should not route a command or force console input."""
        mock_listen.side_effect = [
            {
                "text": "",
                "source": "voice",
                "used_fallback": False,
                "status": "voice_unrecognized",
            },
            {
                "text": "exit",
                "source": "console",
                "used_fallback": False,
                "status": "ok",
            },
        ]
        mock_route_command.return_value = {
            "success": True,
            "message": "Stopping now.",
            "data": {"should_exit": True},
        }

        assistant = MakiBotAssistant(
            settings={**_TEST_SETTINGS, "wake_word_enabled": True}
        )
        assistant.run()

        spoken_messages = [call.args[0] for call in mock_speak.call_args_list]
        self.assertIn("Say 'hey maki' to wake me", spoken_messages[0])
        self.assertEqual(mock_route_command.call_count, 1)
        self.assertEqual(mock_add_history_entry.call_count, 1)
        mock_load_app_registry.assert_called_once()

    @patch("app.assistant.load_app_registry", return_value={"apps": {}, "folders": {}})
    @patch("app.assistant.add_history_entry")
    @patch("app.assistant.speak")
    @patch("app.assistant.route_command")
    @patch("app.assistant.listen")
    def test_run_offers_console_fallback_after_a_voice_miss(
        self,
        mock_listen,
        mock_route_command,
        mock_speak,
        mock_add_history_entry,
        mock_load_app_registry,
    ) -> None:
        """A missed voice turn should quickly allow a typed command instead of looping forever."""
        mock_listen.side_effect = [
            {
                "text": "",
                "source": "voice",
                "used_fallback": False,
                "status": "voice_unrecognized",
            },
            {
                "text": "help",
                "source": "console",
                "used_fallback": False,
                "status": "ok",
            },
        ]
        mock_route_command.return_value = {
            "success": True,
            "message": "Stopping now.",
            "data": {"should_exit": True},
        }

        assistant = MakiBotAssistant(
            settings={**_TEST_SETTINGS, "wake_word_enabled": True}
        )
        assistant.run()

        spoken_messages = [call.args[0] for call in mock_speak.call_args_list]
        self.assertIn("Voice input is not catching anything.", spoken_messages[1])
        self.assertEqual(mock_route_command.call_count, 1)
        self.assertEqual(mock_add_history_entry.call_count, 1)
        self.assertTrue(mock_listen.call_args_list[0].kwargs["settings"]["wake_word_enabled"])
        self.assertFalse(mock_listen.call_args_list[1].kwargs["settings"]["speech_input_enabled"])
        self.assertTrue(mock_listen.call_args_list[1].kwargs["settings"]["wake_word_enabled"])
        self.assertTrue(mock_listen.call_args_list[1].kwargs["settings"]["console_wake_word_optional"])
        mock_load_app_registry.assert_called_once()

    @patch("app.assistant.load_app_registry", return_value={"apps": {}, "folders": {}})
    @patch("app.assistant.add_history_entry")
    @patch("app.assistant.speak")
    @patch("app.assistant.route_command")
    @patch("app.assistant.listen")
    def test_run_accepts_typed_wake_phrase_after_console_fallback(
        self,
        mock_listen,
        mock_route_command,
        mock_speak,
        mock_add_history_entry,
        mock_load_app_registry,
    ) -> None:
        """Typing only the wake phrase during fallback should arm the next command."""
        mock_listen.side_effect = [
            {
                "text": "",
                "source": "voice",
                "used_fallback": False,
                "status": "voice_unrecognized",
            },
            {
                "text": "",
                "source": "console",
                "used_fallback": True,
                "status": "wake_word_only",
            },
            {
                "text": "open chrome",
                "source": "voice",
                "used_fallback": False,
                "status": "ok",
            },
        ]
        mock_route_command.return_value = {
            "success": True,
            "message": "Stopping now.",
            "data": {"should_exit": True},
        }

        assistant = MakiBotAssistant(
            settings={**_TEST_SETTINGS, "wake_word_enabled": True}
        )
        assistant.run()

        spoken_messages = [call.args[0] for call in mock_speak.call_args_list]
        self.assertIn("Voice input is not catching anything.", spoken_messages[1])
        self.assertIn("I'm listening.", spoken_messages[2])
        self.assertEqual(mock_route_command.call_count, 1)
        self.assertEqual(mock_add_history_entry.call_count, 1)
        mock_load_app_registry.assert_called_once()

    @patch("app.assistant.load_app_registry", return_value={"apps": {}, "folders": {}})
    @patch("app.assistant.add_history_entry")
    @patch("app.assistant.route_command")
    def test_confirmation_flow_still_executes_after_yes(
        self,
        mock_route_command,
        mock_add_history_entry,
        mock_load_app_registry,
    ) -> None:
        """The pending confirmation flow should still work with the new input contract."""

        def _route_side_effect(
            intent: dict[str, str],
            settings=None,
            app_registry=None,
            logger=None,
            confirmed: bool = False,
        ) -> dict[str, object]:
            if not confirmed:
                return {
                    "success": True,
                    "message": "Are you sure?",
                    "data": {
                        "status": "pending_confirmation",
                        "requires_confirmation": True,
                    },
                }

            return {
                "success": True,
                "message": "Shutdown blocked for safety.",
                "data": {"status": "blocked", "executed": False},
            }

        mock_route_command.side_effect = _route_side_effect

        assistant = MakiBotAssistant(settings=dict(_TEST_SETTINGS))
        first_result = assistant.handle_text("shutdown computer", source="voice")
        second_result = assistant.handle_text("yes", source="voice")

        self.assertEqual(first_result["data"]["status"], "pending_confirmation")
        self.assertIsNone(assistant.pending_confirmation)
        self.assertTrue(second_result["message"].startswith("Confirmed."))
        self.assertTrue(mock_route_command.call_args_list[1].kwargs["confirmed"])
        self.assertEqual(mock_add_history_entry.call_count, 2)
        mock_load_app_registry.assert_called_once()

    @patch("app.assistant.load_app_registry", return_value={"apps": {}, "folders": {}})
    @patch("app.assistant.add_history_entry")
    @patch("app.assistant.parse_intent_with_llm")
    @patch("app.assistant.parse_intent")
    @patch("app.assistant.route_command")
    def test_handle_text_uses_llm_when_rule_parser_returns_unknown(
        self,
        mock_route_command,
        mock_parse_intent,
        mock_parse_intent_with_llm,
        mock_add_history_entry,
        mock_load_app_registry,
    ) -> None:
        """Unknown rule parses should fall through to the LLM parser."""
        mock_parse_intent.return_value = {
            "intent": "unknown",
            "target": "could you pull up chrome for me",
            "raw_text": "could you pull up chrome for me",
        }
        mock_parse_intent_with_llm.return_value = {
            "intent": "open_app",
            "target": "chrome",
            "raw_text": "could you pull up chrome for me",
        }
        mock_route_command.return_value = {
            "success": True,
            "message": "Opening chrome.",
            "data": {"status": "completed"},
        }

        assistant = MakiBotAssistant(settings=dict(_TEST_SETTINGS))
        result = assistant.handle_text("could you pull up chrome for me", source="voice")

        self.assertTrue(result["success"])
        self.assertEqual(mock_route_command.call_args.args[0]["intent"], "open_app")
        mock_parse_intent_with_llm.assert_called_once()
        mock_add_history_entry.assert_called_once()
        mock_load_app_registry.assert_called_once()

    @patch("app.assistant.load_app_registry", return_value={"apps": {}, "folders": {}})
    @patch("app.assistant.add_history_entry")
    @patch("app.assistant.parse_intent_with_llm")
    @patch("app.assistant.parse_intent")
    @patch("app.assistant.route_command")
    def test_handle_text_keeps_rule_parse_without_llm_for_known_intent(
        self,
        mock_route_command,
        mock_parse_intent,
        mock_parse_intent_with_llm,
        mock_add_history_entry,
        mock_load_app_registry,
    ) -> None:
        """Known rule-based commands should not invoke the LLM parser."""
        mock_parse_intent.return_value = {
            "intent": "open_app",
            "target": "chrome",
            "raw_text": "open chrome",
        }
        mock_route_command.return_value = {
            "success": True,
            "message": "Opening chrome.",
            "data": {"status": "completed"},
        }

        assistant = MakiBotAssistant(settings=dict(_TEST_SETTINGS))
        result = assistant.handle_text("open chrome", source="voice")

        self.assertTrue(result["success"])
        mock_parse_intent_with_llm.assert_not_called()
        mock_add_history_entry.assert_called_once()
        mock_load_app_registry.assert_called_once()


# TODO: Add tests for auto-cancelled pending confirmations from new commands.
if __name__ == "__main__":
    unittest.main()
