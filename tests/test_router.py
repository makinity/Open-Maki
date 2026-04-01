"""Tests for the Phase 3 command router used by MakiBot."""

import unittest
from unittest.mock import patch

from app.brain.command_router import route_command


class CommandRouterTests(unittest.TestCase):
    """Verify safe router behavior for Phase 3 commands."""

    def test_route_time_command_returns_success(self) -> None:
        """The router should return a friendly time response."""
        result = route_command({"intent": "tell_time", "target": "", "raw_text": "what time is it"})

        self.assertTrue(result["success"])
        self.assertIn("current time", result["message"].lower())
        self.assertEqual(result["data"]["status"], "completed")

    def test_route_help_command_returns_command_list(self) -> None:
        """The router should return help text with command data."""
        result = route_command({"intent": "help", "target": "", "raw_text": "help"})

        self.assertTrue(result["success"])
        self.assertIn("commands", result["data"])
        self.assertGreater(len(result["data"]["commands"]), 0)

    def test_route_shutdown_requires_confirmation(self) -> None:
        """Shutdown should not execute until it is confirmed."""
        result = route_command(
            {"intent": "shutdown_computer", "target": "computer", "raw_text": "shutdown computer"},
            settings={"require_confirmation": True, "allow_system_commands": False},
        )

        self.assertTrue(result["success"])
        self.assertTrue(result["data"]["requires_confirmation"])
        self.assertEqual(result["data"]["status"], "pending_confirmation")

    def test_route_confirmed_shutdown_stays_safe_when_disabled(self) -> None:
        """Confirmed shutdown should still be blocked when system commands are disabled."""
        result = route_command(
            {"intent": "shutdown_computer", "target": "computer", "raw_text": "shutdown computer"},
            settings={"require_confirmation": True, "allow_system_commands": False},
            confirmed=True,
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["status"], "blocked")
        self.assertFalse(result["data"]["executed"])

    def test_route_open_folder_not_found(self) -> None:
        """Unknown folders should fail safely."""
        result = route_command(
            {"intent": "open_folder", "target": "folder_that_does_not_exist", "raw_text": "open folder folder_that_does_not_exist"}
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["data"]["status"], "not_found")

    @patch("app.actions.web.webbrowser.open_new_tab", return_value=True)
    def test_route_open_website_returns_success(self, mock_open_new_tab) -> None:
        """The router should return a valid result for website commands."""
        result = route_command(
            {"intent": "open_website", "target": "youtube", "raw_text": "open youtube"}
        )

        self.assertEqual(
            result,
            {
                "success": True,
                "message": "Opening YouTube.",
                "data": None,
            },
        )
        mock_open_new_tab.assert_called_once_with("https://www.youtube.com")

    @patch("app.actions.web.webbrowser.open_new_tab", return_value=True)
    def test_route_search_google_returns_success(self, mock_open_new_tab) -> None:
        """The router should return a valid result for Google searches."""
        result = route_command(
            {
                "intent": "search_google",
                "target": "python decorators",
                "raw_text": "search google for python decorators",
            }
        )

        self.assertEqual(
            result,
            {
                "success": True,
                "message": "Searching Google for python decorators.",
                "data": None,
            },
        )
        mock_open_new_tab.assert_called_once_with(
            "https://www.google.com/search?q=python+decorators"
        )

    @patch("app.actions.web.webbrowser.open_new_tab", return_value=True)
    def test_route_search_youtube_returns_success(self, mock_open_new_tab) -> None:
        """The router should return a valid result for YouTube searches."""
        result = route_command(
            {
                "intent": "search_youtube",
                "target": "jazz piano",
                "raw_text": "search youtube for jazz piano",
            }
        )

        self.assertEqual(
            result,
            {
                "success": True,
                "message": "Searching YouTube for jazz piano.",
                "data": None,
            },
        )
        mock_open_new_tab.assert_called_once_with(
            "https://www.youtube.com/results?search_query=jazz+piano"
        )

    @patch("app.actions.apps.subprocess.Popen")
    def test_route_open_app_uses_nested_registry_aliases(self, mock_popen) -> None:
        """Open-app routing should work with the nested Phase 3 registry structure."""
        result = route_command(
            {"intent": "open_app", "target": "chrome", "raw_text": "open chrome"},
            app_registry={
                "apps": {
                    "chrome": {
                        "name": "chrome",
                        "command": ["chrome"],
                    }
                },
                "folders": {},
            },
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "Opening chrome.")
        mock_popen.assert_called_once_with(["chrome"])

    def test_route_unknown_command_returns_failure(self) -> None:
        """The router should reject unsupported commands cleanly."""
        result = route_command({"intent": "unknown", "target": "dance for me", "raw_text": "dance for me"})

        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "I did not understand that command.")
        self.assertEqual(result["data"]["status"], "unknown")


# TODO: Add router tests for browser failure cases and folder aliases.
if __name__ == "__main__":
    unittest.main()
