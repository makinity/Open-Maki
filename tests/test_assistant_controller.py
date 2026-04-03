"""Tests for assistant controller behavior used by the desktop UI bridge."""

import unittest
from unittest.mock import patch

from app.controllers.assistant_controller import AssistantController

_TEST_SETTINGS = {
    "bot_name": "Maki",
    "conversation_mode_enabled": False,
    "history_limit": 10,
    "require_confirmation": True,
}


class AssistantControllerUiTests(unittest.TestCase):
    """Verify controller behavior needed for the desktop UI command path."""

    @patch("app.controllers.assistant_controller.load_knowledge_profile", return_value={})
    @patch("app.controllers.assistant_controller.load_knowledge_text", return_value="")
    @patch("app.controllers.assistant_controller.load_app_registry", return_value={"apps": {}, "folders": {}})
    def test_build_ready_message_defaults_to_owner_greeting(
        self,
        mock_load_app_registry,
        mock_load_knowledge_text,
        mock_load_knowledge_profile,
    ) -> None:
        """Startup prompts should greet the owner even without a custom profile entry."""
        controller = AssistantController(settings=dict(_TEST_SETTINGS))

        message = controller._build_ready_message()

        self.assertEqual(message, "Good day, sir. Ready. Say or type a command.")
        mock_load_app_registry.assert_called_once()
        mock_load_knowledge_text.assert_called_once()
        mock_load_knowledge_profile.assert_called_once()

    @patch("app.controllers.assistant_controller.load_knowledge_profile", return_value={})
    @patch("app.controllers.assistant_controller.load_knowledge_text", return_value="")
    @patch("app.controllers.assistant_controller.load_app_registry", return_value={"apps": {}, "folders": {}})
    @patch("app.controllers.assistant_controller.add_history_entry")
    @patch(
        "app.controllers.assistant_controller.route_command",
        return_value={
            "success": True,
            "message": "Opening chrome.",
            "data": {"status": "completed"},
        },
    )
    @patch(
        "app.controllers.assistant_controller.parse_intent",
        return_value={
            "intent": "open_app",
            "target": "chrome",
            "raw_text": "open chrome",
        },
    )
    def test_handle_text_records_ui_source_in_history(
        self,
        mock_parse_intent,
        mock_route_command,
        mock_add_history_entry,
        mock_load_app_registry,
        mock_load_knowledge_text,
        mock_load_knowledge_profile,
    ) -> None:
        """UI-issued commands should keep source='ui' when saved to history."""
        controller = AssistantController(settings=dict(_TEST_SETTINGS))

        result = controller.handle_text("open chrome", source="ui")

        self.assertTrue(result["success"])
        self.assertEqual(mock_add_history_entry.call_args.kwargs["source"], "ui")
        mock_parse_intent.assert_called_once_with("open chrome")
        mock_route_command.assert_called_once()
        mock_load_app_registry.assert_called_once()
        mock_load_knowledge_text.assert_called_once()
        mock_load_knowledge_profile.assert_called_once()


if __name__ == "__main__":
    unittest.main()
