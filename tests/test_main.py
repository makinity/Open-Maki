"""Tests for DB-required application startup."""

import unittest
from unittest.mock import MagicMock, patch

from app.main import main


class MainStartupTests(unittest.TestCase):
    """Verify startup behavior when the required database is unavailable."""

    @patch("app.main.MakiBotAssistant")
    @patch("app.main.load_settings")
    @patch("app.main.get_database_error", return_value="db unavailable")
    @patch("app.main.initialize_database", return_value=False)
    @patch("app.main.get_logger")
    @patch("app.main.configure_logging")
    def test_main_fails_fast_when_database_is_unavailable(
        self,
        mock_configure_logging,
        mock_get_logger,
        mock_initialize_database,
        mock_get_database_error,
        mock_load_settings,
        mock_assistant,
    ) -> None:
        """Startup should stop before creating the assistant when MySQL is unavailable."""
        logger = MagicMock()
        mock_get_logger.return_value = logger

        result = main()

        self.assertEqual(result, 1)
        mock_configure_logging.assert_called_once()
        mock_initialize_database.assert_called_once_with(logger=logger)
        mock_get_database_error.assert_called_once_with()
        logger.error.assert_called_once_with("Startup aborted: %s", "db unavailable")
        mock_load_settings.assert_not_called()
        mock_assistant.assert_not_called()


if __name__ == "__main__":
    unittest.main()
