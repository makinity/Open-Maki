"""Tests for the desktop UI bridge scaffold."""

import unittest
from unittest.mock import patch

from app.ui_api import MakiUIApi


class _FakeAssistantController:
    """Simple stateful controller stub for UI bridge tests."""

    def __init__(self, settings: dict[str, object] | None = None) -> None:
        self.settings = dict(settings or {})
        self.bot_name = str(self.settings.get("bot_name", "Maki"))
        self.calls: list[tuple[str, str]] = []
        self.say_calls: list[str] = []
        self._pending_shutdown = False

    def handle_text(self, text: str, source: str = "console") -> dict[str, object]:
        self.calls.append((text, source))

        if text == "raise error":
            raise RuntimeError("controller exploded")

        if text == "shutdown computer":
            self._pending_shutdown = True
            return {
                "success": True,
                "message": "Are you sure you want me to shut down the computer? Say yes to confirm or no to cancel.",
                "data": {
                    "status": "pending_confirmation",
                    "requires_confirmation": True,
                },
            }

        if text == "yes" and self._pending_shutdown:
            self._pending_shutdown = False
            return {
                "success": True,
                "message": "Confirmed. Shutdown blocked for safety.",
                "data": {
                    "status": "blocked",
                    "confirmed": True,
                },
            }

        if text == "exit":
            return {
                "success": True,
                "message": "Goodbye for now.",
                "data": {
                    "status": "completed",
                    "should_exit": True,
                },
            }

        if text == "what is this":
            return {
                "success": False,
                "message": "I did not understand that command.",
                "data": {
                    "status": "unknown",
                },
            }

        return {
            "success": True,
            "message": "Opening chrome.",
            "data": {
                "status": "completed",
            },
        }

    def say(self, message: str, use_tts: bool = True) -> None:
        self.say_calls.append(message)


class MakiUIApiTests(unittest.TestCase):
    """Verify the in-memory bridge payloads for the desktop scaffold."""

    def test_get_bootstrap_data_returns_status_and_activity(self) -> None:
        """Bootstrap data should include the bot name, status, and session activity."""
        api = MakiUIApi(
            assistant_controller=_FakeAssistantController(settings={"bot_name": "Maki Prime"})
        )

        payload = api.get_bootstrap_data()

        self.assertEqual(payload["bot_name"], "Maki Prime")
        self.assertEqual(payload["status"]["state"], "ready")
        self.assertFalse(payload["mic_active"])
        self.assertTrue(payload["auto_listen_enabled"])
        self.assertEqual(payload["activity"][0]["type"], "system")

    def test_send_command_rejects_empty_input(self) -> None:
        """Blank commands should return a friendly validation response."""
        fake_controller = _FakeAssistantController(settings={"bot_name": "Maki"})
        api = MakiUIApi(assistant_controller=fake_controller)

        payload = api.send_command("   ")

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["command"], "")
        self.assertEqual(payload["status"]["state"], "error")
        self.assertEqual(payload["meta"]["result_status"], "validation_error")
        self.assertEqual(fake_controller.calls, [])
        self.assertIn("Type a command", payload["response"])

    def test_send_command_calls_assistant_controller_with_ui_source(self) -> None:
        """Typed UI commands should go through the real controller contract with source='ui'."""
        fake_controller = _FakeAssistantController(settings={"bot_name": "Maki"})
        api = MakiUIApi(assistant_controller=fake_controller)

        payload = api.send_command("open chrome")

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "open chrome")
        self.assertEqual(payload["response"], "Opening chrome.")
        self.assertEqual(payload["status"]["state"], "ready")
        self.assertEqual(payload["meta"]["source"], "ui")
        self.assertEqual(payload["meta"]["result_status"], "completed")
        self.assertEqual(fake_controller.calls, [("open chrome", "ui")])
        self.assertEqual(fake_controller.say_calls, ["Opening chrome."])
        self.assertEqual(payload["activity"][-2]["type"], "user")
        self.assertEqual(payload["activity"][-1]["type"], "assistant")

    def test_send_command_preserves_confirmation_flow_on_one_api_instance(self) -> None:
        """One UI API instance should preserve the controller state across commands."""
        fake_controller = _FakeAssistantController(settings={"bot_name": "Maki"})
        api = MakiUIApi(assistant_controller=fake_controller)

        first_payload = api.send_command("shutdown computer")
        second_payload = api.send_command("yes")

        self.assertTrue(first_payload["ok"])
        self.assertTrue(first_payload["meta"]["requires_confirmation"])
        self.assertEqual(first_payload["meta"]["result_status"], "pending_confirmation")
        self.assertTrue(second_payload["ok"])
        self.assertEqual(second_payload["meta"]["result_status"], "blocked")
        self.assertEqual(
            fake_controller.say_calls,
            [
                "Are you sure you want me to shut down the computer? Say yes to confirm or no to cancel.",
                "Confirmed. Shutdown blocked for safety.",
            ],
        )
        self.assertEqual(
            fake_controller.calls,
            [("shutdown computer", "ui"), ("yes", "ui")],
        )

    def test_send_command_returns_idle_status_for_exit_commands(self) -> None:
        """Exit-style commands should stay in the UI and return should_exit metadata."""
        fake_controller = _FakeAssistantController(settings={"bot_name": "Maki"})
        api = MakiUIApi(assistant_controller=fake_controller)

        payload = api.send_command("exit")

        self.assertTrue(payload["ok"])
        self.assertTrue(payload["meta"]["should_exit"])
        self.assertEqual(payload["status"]["state"], "idle")
        self.assertEqual(payload["response"], "Goodbye for now.")
        self.assertEqual(fake_controller.say_calls, ["Goodbye for now."])

    def test_send_command_keeps_unknown_backend_replies_nonfatal(self) -> None:
        """Unknown-command backend replies should remain visible without an error status."""
        fake_controller = _FakeAssistantController(settings={"bot_name": "Maki"})
        api = MakiUIApi(assistant_controller=fake_controller)

        payload = api.send_command("what is this")

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["meta"]["result_status"], "unknown")
        self.assertEqual(payload["status"]["state"], "ready")
        self.assertEqual(payload["response"], "I did not understand that command.")
        self.assertEqual(fake_controller.say_calls, ["I did not understand that command."])

    def test_send_command_handles_controller_exceptions(self) -> None:
        """Backend exceptions should return an error status and a system activity item."""
        fake_controller = _FakeAssistantController(settings={"bot_name": "Maki"})
        api = MakiUIApi(assistant_controller=fake_controller)

        payload = api.send_command("raise error")

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["status"]["state"], "error")
        self.assertEqual(payload["meta"]["result_status"], "error")
        self.assertEqual(fake_controller.say_calls, [])
        self.assertEqual(payload["activity"][-1]["type"], "system")
        self.assertIn("Something went wrong", payload["response"])

    @patch(
        "app.ui_api.listen",
        return_value={
            "text": "open chrome",
            "source": "voice",
            "used_fallback": False,
            "status": "ok",
        },
    )
    def test_toggle_mic_captures_voice_and_routes_it_to_the_backend(self, mock_listen) -> None:
        """The mic button should capture one voice command and process it through the backend."""
        fake_controller = _FakeAssistantController(settings={"bot_name": "Maki"})
        api = MakiUIApi(assistant_controller=fake_controller)

        payload = api.toggle_mic()

        self.assertTrue(payload["ok"])
        self.assertFalse(payload["mic_active"])
        self.assertEqual(payload["command"], "open chrome")
        self.assertEqual(payload["response"], "Opening chrome.")
        self.assertEqual(payload["meta"]["source"], "voice")
        self.assertEqual(payload["status"]["state"], "ready")
        self.assertEqual(fake_controller.calls, [("open chrome", "voice")])
        self.assertEqual(fake_controller.say_calls, ["Opening chrome."])

        listen_settings = mock_listen.call_args.kwargs["settings"]
        self.assertTrue(listen_settings["speech_input_enabled"])
        self.assertFalse(listen_settings["console_fallback_enabled"])
        self.assertFalse(listen_settings["wake_word_enabled"])

    @patch(
        "app.ui_api.listen",
        return_value={
            "text": "",
            "source": "voice",
            "used_fallback": False,
            "status": "voice_timeout",
        },
    )
    def test_toggle_mic_returns_ready_status_when_no_voice_is_captured(self, mock_listen) -> None:
        """A voice timeout should return a nonfatal system message and keep the UI usable."""
        fake_controller = _FakeAssistantController(settings={"bot_name": "Maki"})
        api = MakiUIApi(assistant_controller=fake_controller)

        payload = api.toggle_mic()

        self.assertFalse(payload["ok"])
        self.assertFalse(payload["mic_active"])
        self.assertEqual(payload["meta"]["result_status"], "voice_timeout")
        self.assertEqual(payload["status"]["state"], "ready")
        self.assertEqual(payload["response"], "I didn't hear anything.")
        self.assertEqual(fake_controller.calls, [])
        self.assertEqual(fake_controller.say_calls, ["I didn't hear anything."])
        self.assertEqual(payload["activity"][-1]["type"], "system")

    @patch(
        "app.ui_api.listen",
        return_value={
            "text": "",
            "source": "voice",
            "used_fallback": False,
            "status": "voice_timeout",
        },
    )
    def test_toggle_mic_can_suppress_empty_voice_feedback_in_auto_mode(self, mock_listen) -> None:
        """Auto-listen mode should not speak or log every empty timeout result."""
        fake_controller = _FakeAssistantController(settings={"bot_name": "Maki"})
        api = MakiUIApi(assistant_controller=fake_controller)

        payload = api.toggle_mic(silent_empty_results=True)

        self.assertFalse(payload["ok"])
        self.assertFalse(payload["mic_active"])
        self.assertEqual(payload["meta"]["result_status"], "voice_timeout")
        self.assertEqual(payload["status"]["state"], "ready")
        self.assertEqual(payload["status"]["label"], "Voice standby is active.")
        self.assertEqual(payload["response"], "I didn't hear anything.")
        self.assertEqual(fake_controller.calls, [])
        self.assertEqual(fake_controller.say_calls, [])
        self.assertEqual(len(payload["activity"]), 1)
        mock_listen.assert_called_once()


if __name__ == "__main__":
    unittest.main()
