"""Tests for the command router used by Maki."""

import unittest
from unittest.mock import MagicMock, patch

from app.brain.command_router import route_command


class CommandRouterTests(unittest.TestCase):
    """Verify safe router behavior for assistant commands."""

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

    @patch("app.actions.system.get_available_voices")
    def test_route_list_voices_returns_voice_data(self, mock_get_available_voices) -> None:
        """The router should return the available TTS voices."""
        mock_get_available_voices.return_value = [
            {
                "id": "voice-1",
                "name": "Microsoft David Desktop - English (United States)",
                "languages": "en-US",
                "gender": "Male",
                "age": "Adult",
            }
        ]

        result = route_command({"intent": "list_voices", "target": "", "raw_text": "list voices"})

        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["status"], "completed")
        self.assertEqual(len(result["data"]["voices"]), 1)
        self.assertIn("David", result["message"])

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

    @patch("app.actions.web.load_website_aliases", return_value={})
    @patch("app.actions.web.webbrowser.open_new_tab", return_value=True)
    def test_route_open_website_returns_success(
        self,
        mock_open_new_tab,
        mock_load_website_aliases,
    ) -> None:
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
        mock_load_website_aliases.assert_called_once_with()
        mock_open_new_tab.assert_called_once_with("https://www.youtube.com")

    @patch("app.actions.web.load_website_aliases", return_value={})
    @patch("app.actions.web.webbrowser.open_new_tab", return_value=True)
    def test_route_open_flutterflow_uses_built_in_alias(
        self,
        mock_open_new_tab,
        mock_load_website_aliases,
    ) -> None:
        """Built-in FlutterFlow should open without LLM inference."""
        result = route_command(
            {"intent": "open_website", "target": "flutterflow", "raw_text": "open flutterflow"}
        )

        self.assertEqual(
            result,
            {
                "success": True,
                "message": "Opening FlutterFlow.",
                "data": None,
            },
        )
        mock_load_website_aliases.assert_called_once_with()
        mock_open_new_tab.assert_called_once_with("https://www.flutterflow.io")

    @patch("app.actions.web.load_website_aliases", return_value={})
    @patch("app.actions.web.webbrowser.open_new_tab", return_value=True)
    def test_route_open_common_dev_sites_use_built_in_aliases(
        self,
        mock_open_new_tab,
        mock_load_website_aliases,
    ) -> None:
        """Common developer sites should open directly from the built-in alias list."""
        expected_sites = {
            "vercel": ("Vercel", "https://vercel.com"),
            "netlify": ("Netlify", "https://www.netlify.com"),
            "supabase": ("Supabase", "https://supabase.com"),
            "firebase": ("Firebase", "https://firebase.google.com"),
        }

        for alias, (display_name, url) in expected_sites.items():
            with self.subTest(alias=alias):
                result = route_command(
                    {"intent": "open_website", "target": alias, "raw_text": f"open {alias}"}
                )
                self.assertEqual(
                    result,
                    {
                        "success": True,
                        "message": f"Opening {display_name}.",
                        "data": None,
                    },
                )

        self.assertEqual(mock_load_website_aliases.call_count, len(expected_sites))
        self.assertEqual(
            [call.args[0] for call in mock_open_new_tab.call_args_list],
            [site[1] for site in expected_sites.values()],
        )

    @patch("app.actions.web.load_website_aliases", return_value={})
    @patch("app.actions.web.request_text_response", return_value='{"name": "Reddit", "url": "https://www.reddit.com"}')
    @patch("app.actions.web.webbrowser.open_new_tab", return_value=True)
    def test_route_open_website_uses_llm_inference_for_unknown_sites(
        self,
        mock_open_new_tab,
        mock_request_text_response,
        mock_load_website_aliases,
    ) -> None:
        """Unknown site names should fall through to the clean LLM website inference path."""
        logger = MagicMock()

        result = route_command(
            {"intent": "open_website", "target": "reddit", "raw_text": "open reddit"},
            settings={"llm_provider": "auto"},
            logger=logger,
        )

        self.assertEqual(
            result,
            {
                "success": True,
                "message": "Opening Reddit.",
                "data": None,
            },
        )
        mock_load_website_aliases.assert_called_once_with()
        mock_request_text_response.assert_called_once()
        self.assertEqual(mock_request_text_response.call_args.kwargs["settings"], {"llm_provider": "auto"})
        self.assertIs(mock_request_text_response.call_args.kwargs["logger"], logger)
        mock_open_new_tab.assert_called_once_with("https://www.reddit.com")

    @patch("app.actions.web.load_website_aliases", return_value={})
    @patch("app.actions.web.webbrowser.open_new_tab", return_value=True)
    def test_route_search_google_returns_success(
        self,
        mock_open_new_tab,
        mock_load_website_aliases,
    ) -> None:
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
        mock_load_website_aliases.assert_called_once_with()
        mock_open_new_tab.assert_called_once_with(
            "https://www.google.com/search?q=python+decorators"
        )

    @patch(
        "app.actions.web.load_website_aliases",
        return_value={
            "github": {
                "name": "GitHub",
                "url": "https://github.com",
                "search_url_template": "https://github.com/search?q={query}",
            }
        },
    )
    @patch("app.actions.web.webbrowser.open_new_tab", return_value=True)
    def test_route_search_website_returns_success(
        self,
        mock_open_new_tab,
        mock_load_website_aliases,
    ) -> None:
        """The router should search any DB-backed website alias with a search URL template."""
        result = route_command(
            {
                "intent": "search_website",
                "site": "github",
                "target": "makibot",
                "raw_text": "search github for makibot",
            }
        )

        self.assertEqual(
            result,
            {
                "success": True,
                "message": "Searching GitHub for makibot.",
                "data": None,
            },
        )
        mock_load_website_aliases.assert_called_once_with()
        mock_open_new_tab.assert_called_once_with(
            "https://github.com/search?q=makibot"
        )

    @patch("app.actions.web.load_website_aliases", return_value={})
    @patch("app.actions.web.webbrowser.open_new_tab", return_value=True)
    def test_route_search_youtube_returns_success(
        self,
        mock_open_new_tab,
        mock_load_website_aliases,
    ) -> None:
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
        mock_load_website_aliases.assert_called_once_with()
        mock_open_new_tab.assert_called_once_with(
            "https://www.youtube.com/results?search_query=jazz+piano"
        )

    @patch("app.actions.apps.subprocess.Popen")
    def test_route_open_app_uses_nested_registry_aliases(self, mock_popen) -> None:
        """Open-app routing should work with the nested registry structure."""
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

    def test_route_open_app_not_found_mentions_database_table(self) -> None:
        """Missing app aliases should point the user to the database-backed source."""
        result = route_command(
            {"intent": "open_app", "target": "unknownapp", "raw_text": "open unknownapp"},
            app_registry={"apps": {}, "folders": {}},
        )

        self.assertFalse(result["success"])
        self.assertIn("app_aliases table", result["message"])
        self.assertNotIn("apps.json", result["message"])

    def test_route_unknown_command_returns_failure(self) -> None:
        """The router should reject unsupported commands cleanly."""
        result = route_command({"intent": "unknown", "target": "dance for me", "raw_text": "dance for me"})

        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "I did not understand that command.")
        self.assertEqual(result["data"]["status"], "unknown")


# TODO: Add router tests for browser failure cases and folder aliases.
if __name__ == "__main__":
    unittest.main()


