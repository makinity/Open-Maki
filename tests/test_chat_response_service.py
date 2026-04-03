"""Tests for LLM-backed response helpers."""

import unittest
from unittest.mock import patch

from app.services.chat_response_service import build_startup_greeting


class ChatResponseServiceTests(unittest.TestCase):
    """Verify Groq-backed startup greeting behavior."""

    @patch(
        "app.services.chat_response_service.request_text_response",
        return_value="  Good evening, Sir. It is good to see you again.  ",
    )
    @patch("app.services.chat_response_service.get_llm_api_key", return_value="groq-test-key")
    def test_build_startup_greeting_uses_groq_and_knowledge_profile(
        self,
        mock_get_llm_api_key,
        mock_request_text_response,
    ) -> None:
        """Startup greetings should use the Groq path and owner title from knowledge."""
        greeting = build_startup_greeting(
            settings={"llm_provider": "auto", "llm_model": "openai/gpt-oss-20b"},
            knowledge_text="Preferred title: Sir\nStartup greeting: Good day, sir.",
            knowledge_profile={"preferred_title": "Sir", "startup_greeting": "Good day, sir."},
            logger=None,
        )

        self.assertEqual(greeting, "Good evening, Sir. It is good to see you again.")
        mock_get_llm_api_key.assert_called_once_with("groq")
        self.assertEqual(
            mock_request_text_response.call_args.kwargs["settings"]["llm_provider"],
            "groq",
        )
        self.assertIn(
            "Address the owner as Sir.",
            mock_request_text_response.call_args.kwargs["messages"][1]["content"],
        )
        self.assertIn(
            "Treat this preferred startup style as inspiration only",
            mock_request_text_response.call_args.kwargs["messages"][1]["content"],
        )

    @patch("app.services.chat_response_service.request_text_response", return_value="Good day, sir.")
    @patch("app.services.chat_response_service.get_llm_api_key", return_value="groq-test-key")
    def test_build_startup_greeting_expands_overly_generic_output(
        self,
        mock_get_llm_api_key,
        mock_request_text_response,
    ) -> None:
        """A too-short or copied greeting should be expanded into a fuller startup line."""
        greeting = build_startup_greeting(
            settings={"llm_provider": "auto", "llm_model": "openai/gpt-oss-20b"},
            knowledge_text="Preferred title: Sir\nStartup greeting: Good day, sir.",
            knowledge_profile={"preferred_title": "Sir", "startup_greeting": "Good day, sir."},
            logger=None,
        )

        self.assertEqual(greeting, "Good day, sir. Maki is ready to help you today, Sir.")
        mock_get_llm_api_key.assert_called_once_with("groq")
        mock_request_text_response.assert_called_once()

    @patch("app.services.chat_response_service.request_text_response")
    @patch("app.services.chat_response_service.get_llm_api_key", return_value="")
    def test_build_startup_greeting_returns_none_without_groq_key(
        self,
        mock_get_llm_api_key,
        mock_request_text_response,
    ) -> None:
        """Startup greeting generation should fail safely when Groq is not configured."""
        greeting = build_startup_greeting(settings={}, knowledge_text="", knowledge_profile={}, logger=None)

        self.assertIsNone(greeting)
        mock_get_llm_api_key.assert_called_once_with("groq")
        mock_request_text_response.assert_not_called()


if __name__ == "__main__":
    unittest.main()

