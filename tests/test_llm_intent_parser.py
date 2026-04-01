"""Tests for the optional xAI-backed LLM intent parser."""

import unittest
from unittest.mock import patch

from app.brain.llm_intent_parser import parse_intent_with_llm

_TEST_SETTINGS = {
    "llm_parser_enabled": True,
    "llm_model": "grok-4.20-reasoning",
    "llm_timeout_seconds": 15,
}

_TEST_REGISTRY = {
    "apps": {
        "chrome": {"name": "chrome", "command": ["chrome"]},
        "spotify": {"name": "spotify", "command": ["spotify"]},
    },
    "folders": {
        "downloads": {"name": "downloads", "path": "C:\\Users\\Maki\\Downloads"},
    },
}


class LlmIntentParserTests(unittest.TestCase):
    """Verify safe normalization and failure handling for LLM parsing."""

    @patch("app.brain.llm_intent_parser.request_intent_tool_call")
    def test_valid_open_app_tool_call_normalizes_to_intent(self, mock_request_intent_tool_call) -> None:
        """A valid tool call should become the existing assistant intent structure."""
        mock_request_intent_tool_call.return_value = {
            "name": "select_intent",
            "arguments": {"intent": "open_app", "target": "chrome"},
        }

        intent = parse_intent_with_llm(
            "could you pull up chrome for me",
            settings=dict(_TEST_SETTINGS),
            app_registry=_TEST_REGISTRY,
        )

        self.assertEqual(
            intent,
            {
                "intent": "open_app",
                "target": "chrome",
                "raw_text": "could you pull up chrome for me",
            },
        )

    @patch("app.brain.llm_intent_parser.request_intent_tool_call")
    def test_valid_open_website_tool_call_normalizes_to_intent(self, mock_request_intent_tool_call) -> None:
        """A website tool call should keep the requested alias target."""
        mock_request_intent_tool_call.return_value = {
            "name": "select_intent",
            "arguments": {"intent": "open_website", "target": "youtube"},
        }

        intent = parse_intent_with_llm(
            "please take me to youtube",
            settings=dict(_TEST_SETTINGS),
            app_registry=_TEST_REGISTRY,
        )

        self.assertEqual(intent["intent"], "open_website")
        self.assertEqual(intent["target"], "youtube")

    @patch("app.brain.llm_intent_parser.request_intent_tool_call")
    def test_shutdown_tool_call_normalizes_fixed_target(self, mock_request_intent_tool_call) -> None:
        """Dangerous power actions should normalize to the fixed computer target."""
        mock_request_intent_tool_call.return_value = {
            "name": "select_intent",
            "arguments": {"intent": "shutdown_computer", "target": "ignored value"},
        }

        intent = parse_intent_with_llm(
            "please shut the pc down",
            settings=dict(_TEST_SETTINGS),
            app_registry=_TEST_REGISTRY,
        )

        self.assertEqual(intent["intent"], "shutdown_computer")
        self.assertEqual(intent["target"], "computer")

    @patch("app.brain.llm_intent_parser.request_intent_tool_call")
    def test_invalid_tool_name_returns_none(self, mock_request_intent_tool_call) -> None:
        """Unexpected tool names must be rejected."""
        mock_request_intent_tool_call.return_value = {
            "name": "unsafe_tool",
            "arguments": {"intent": "open_app", "target": "chrome"},
        }

        intent = parse_intent_with_llm(
            "could you open chrome",
            settings=dict(_TEST_SETTINGS),
            app_registry=_TEST_REGISTRY,
        )

        self.assertIsNone(intent)

    @patch("app.brain.llm_intent_parser.request_intent_tool_call")
    def test_missing_required_target_returns_none(self, mock_request_intent_tool_call) -> None:
        """Target-based intents without a target must be rejected."""
        mock_request_intent_tool_call.return_value = {
            "name": "select_intent",
            "arguments": {"intent": "open_app", "target": ""},
        }

        intent = parse_intent_with_llm(
            "open something for me",
            settings=dict(_TEST_SETTINGS),
            app_registry=_TEST_REGISTRY,
        )

        self.assertIsNone(intent)

    @patch("app.brain.llm_intent_parser.request_intent_tool_call", return_value=None)
    def test_no_tool_call_returns_none(self, mock_request_intent_tool_call) -> None:
        """A response without a tool call should not produce an intent."""
        intent = parse_intent_with_llm(
            "do some random thing",
            settings=dict(_TEST_SETTINGS),
            app_registry=_TEST_REGISTRY,
        )

        self.assertIsNone(intent)
        mock_request_intent_tool_call.assert_called_once()

    @patch("app.brain.llm_intent_parser.request_intent_tool_call", side_effect=RuntimeError("timeout"))
    def test_transport_exception_returns_none(self, mock_request_intent_tool_call) -> None:
        """Transport-level exceptions must fail safely."""
        intent = parse_intent_with_llm(
            "could you open spotify",
            settings=dict(_TEST_SETTINGS),
            app_registry=_TEST_REGISTRY,
        )

        self.assertIsNone(intent)
        mock_request_intent_tool_call.assert_called_once()

    @patch("app.brain.llm_intent_parser.request_intent_tool_call")
    def test_unsupported_intent_is_rejected(self, mock_request_intent_tool_call) -> None:
        """The LLM cannot escape the allowed intent list."""
        mock_request_intent_tool_call.return_value = {
            "name": "select_intent",
            "arguments": {"intent": "press_hotkey", "target": "ctrl+w"},
        }

        intent = parse_intent_with_llm(
            "close the window",
            settings=dict(_TEST_SETTINGS),
            app_registry=_TEST_REGISTRY,
        )

        self.assertIsNone(intent)

    @patch("app.brain.llm_intent_parser.request_intent_tool_call")
    def test_alias_context_is_included_in_prompt(self, mock_request_intent_tool_call) -> None:
        """Known app, folder, and website aliases should be provided to the model prompt."""
        mock_request_intent_tool_call.return_value = {
            "name": "select_intent",
            "arguments": {"intent": "open_app", "target": "chrome"},
        }

        parse_intent_with_llm(
            "could you pull up chrome for me",
            settings=dict(_TEST_SETTINGS),
            app_registry=_TEST_REGISTRY,
        )

        messages = mock_request_intent_tool_call.call_args.kwargs["messages"]
        combined_prompt = "\n".join(str(message["content"]) for message in messages)
        self.assertIn("chrome", combined_prompt)
        self.assertIn("downloads", combined_prompt)
        self.assertIn("youtube", combined_prompt)

    def test_disabled_llm_parser_returns_none(self) -> None:
        """LLM parsing should not run when the setting is disabled."""
        intent = parse_intent_with_llm(
            "could you pull up chrome for me",
            settings={**_TEST_SETTINGS, "llm_parser_enabled": False},
            app_registry=_TEST_REGISTRY,
        )

        self.assertIsNone(intent)


if __name__ == "__main__":
    unittest.main()
