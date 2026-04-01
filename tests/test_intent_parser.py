"""Tests for the rule-based intent parser used by MakiBot."""

import unittest
from unittest.mock import patch

from app.brain.intent_parser import parse_intent


class IntentParserTests(unittest.TestCase):
    """Verify the supported Phase 3 intents are parsed consistently."""

    def test_parse_open_app_intent(self) -> None:
        """The parser should detect an application launch command."""
        intent = parse_intent("open chrome")

        self.assertEqual(
            intent,
            {
                "intent": "open_app",
                "target": "chrome",
                "raw_text": "open chrome",
            },
        )

    def test_parse_open_youtube_intent(self) -> None:
        """The parser should detect direct website open commands."""
        intent = parse_intent("open youtube")

        self.assertEqual(intent["intent"], "open_website")
        self.assertEqual(intent["target"], "youtube")

    def test_parse_go_to_gmail_intent(self) -> None:
        """The parser should detect Gmail website commands."""
        intent = parse_intent("go to gmail")

        self.assertEqual(intent["intent"], "open_website")
        self.assertEqual(intent["target"], "gmail")

    def test_parse_search_google_phrase(self) -> None:
        """The parser should detect the longer Google search phrase."""
        intent = parse_intent("search google for python speech recognition")

        self.assertEqual(intent["intent"], "search_google")
        self.assertEqual(intent["target"], "python speech recognition")

    def test_parse_google_shortcut_phrase(self) -> None:
        """The parser should detect the short Google search shortcut."""
        intent = parse_intent("google decorators")

        self.assertEqual(intent["intent"], "search_google")
        self.assertEqual(intent["target"], "decorators")

    def test_parse_search_youtube_phrase(self) -> None:
        """The parser should detect the longer YouTube search phrase."""
        intent = parse_intent("search youtube for jazz piano")

        self.assertEqual(intent["intent"], "search_youtube")
        self.assertEqual(intent["target"], "jazz piano")

    def test_parse_youtube_shortcut_phrase(self) -> None:
        """The parser should detect the short YouTube search shortcut."""
        intent = parse_intent("youtube lofi")

        self.assertEqual(intent["intent"], "search_youtube")
        self.assertEqual(intent["target"], "lofi")

    def test_parse_create_folder_variation(self) -> None:
        """The parser should detect natural folder creation phrases."""
        intent = parse_intent("make a folder called projects")

        self.assertEqual(intent["intent"], "create_folder")
        self.assertEqual(intent["target"], "projects")

    def test_parse_open_folder_intent(self) -> None:
        """The parser should detect folder opening commands."""
        intent = parse_intent("open folder downloads")

        self.assertEqual(intent["intent"], "open_folder")
        self.assertEqual(intent["target"], "downloads")

    def test_parse_shutdown_intent(self) -> None:
        """The parser should detect shutdown requests."""
        intent = parse_intent("shutdown computer")

        self.assertEqual(intent["intent"], "shutdown_computer")
        self.assertEqual(intent["target"], "computer")

    def test_parse_help_intent(self) -> None:
        """The parser should detect help requests."""
        intent = parse_intent("what can you do")

        self.assertEqual(intent["intent"], "help")
        self.assertEqual(intent["target"], "")

    def test_parse_confirmation_reply(self) -> None:
        """The parser should detect confirmation replies."""
        yes_intent = parse_intent("yes")
        no_intent = parse_intent("no")

        self.assertEqual(yes_intent["intent"], "confirm_yes")
        self.assertEqual(no_intent["intent"], "confirm_no")

    @patch("app.brain.intent_parser.load_website_aliases")
    @patch("app.brain.intent_parser.load_command_patterns")
    def test_parse_intent_uses_database_command_templates(
        self,
        mock_load_command_patterns,
        mock_load_website_aliases,
    ) -> None:
        """Database command templates should override the fallback phrase list."""
        mock_load_command_patterns.return_value = [
            {
                "phrase_template": "boot {target}",
                "intent": "open_target",
                "fixed_target": "",
                "priority": 1,
            }
        ]
        mock_load_website_aliases.return_value = {}

        intent = parse_intent("boot chrome")

        self.assertEqual(intent["intent"], "open_app")
        self.assertEqual(intent["target"], "chrome")


# TODO: Add more coverage for quoted targets and direct URLs.
if __name__ == "__main__":
    unittest.main()
