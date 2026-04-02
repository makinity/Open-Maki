"""Tests for the desktop UI startup path."""

import unittest
from unittest.mock import MagicMock, patch

import run_ui


class RunUiTests(unittest.TestCase):
    """Verify startup behavior for the first desktop UI scaffold."""

    @patch("run_ui._get_ui_index_uri")
    @patch("run_ui._import_webview")
    @patch("run_ui.load_settings")
    @patch("run_ui.initialize_database", return_value=True)
    @patch("run_ui.get_logger")
    @patch("run_ui.configure_logging")
    def test_main_opens_desktop_window_after_startup_checks(
        self,
        mock_configure_logging,
        mock_get_logger,
        mock_initialize_database,
        mock_load_settings,
        mock_import_webview,
        mock_get_ui_index_uri,
    ) -> None:
        """The desktop entrypoint should create the window after startup succeeds."""
        logger = MagicMock()
        webview_module = MagicMock()
        mock_get_logger.return_value = logger
        mock_load_settings.return_value = {"bot_name": "Maki"}
        mock_import_webview.return_value = webview_module
        mock_get_ui_index_uri.return_value = "file:///C:/Python/MakiBot/ui/index.html"

        result = run_ui.main()

        self.assertEqual(result, 0)
        mock_configure_logging.assert_called_once()
        mock_initialize_database.assert_called_once_with(logger=logger)
        mock_import_webview.assert_called_once_with()
        mock_get_ui_index_uri.assert_called_once_with()
        webview_module.start.assert_called_once_with(debug=False)

        create_window_kwargs = webview_module.create_window.call_args.kwargs
        self.assertEqual(create_window_kwargs["title"], "Maki")
        self.assertEqual(create_window_kwargs["width"], 1280)
        self.assertEqual(create_window_kwargs["height"], 820)
        self.assertEqual(create_window_kwargs["min_size"], (980, 680))
        self.assertTrue(create_window_kwargs["resizable"])
        self.assertFalse(create_window_kwargs["frameless"])
        self.assertIsInstance(create_window_kwargs["js_api"], run_ui.MakiUIApi)

    @patch("run_ui.load_settings")
    @patch("run_ui.get_database_error", return_value="db unavailable")
    @patch("run_ui.initialize_database", return_value=False)
    @patch("run_ui.get_logger")
    @patch("run_ui.configure_logging")
    def test_main_fails_fast_when_database_is_unavailable(
        self,
        mock_configure_logging,
        mock_get_logger,
        mock_initialize_database,
        mock_get_database_error,
        mock_load_settings,
    ) -> None:
        """The UI should not launch when MySQL startup fails."""
        logger = MagicMock()
        mock_get_logger.return_value = logger

        result = run_ui.main()

        self.assertEqual(result, 1)
        mock_configure_logging.assert_called_once()
        mock_initialize_database.assert_called_once_with(logger=logger)
        mock_get_database_error.assert_called_once_with()
        logger.error.assert_called_once_with("Startup aborted: %s", "db unavailable")
        mock_load_settings.assert_not_called()

    @patch("run_ui._import_webview", side_effect=RuntimeError("pywebview is not installed"))
    @patch("run_ui.load_settings", return_value={"bot_name": "Maki"})
    @patch("run_ui.initialize_database", return_value=True)
    @patch("run_ui.get_logger")
    @patch("run_ui.configure_logging")
    def test_main_fails_when_pywebview_is_missing(
        self,
        mock_configure_logging,
        mock_get_logger,
        mock_initialize_database,
        mock_load_settings,
        mock_import_webview,
    ) -> None:
        """Missing UI dependencies should stop startup with a clear error."""
        logger = MagicMock()
        mock_get_logger.return_value = logger

        result = run_ui.main()

        self.assertEqual(result, 1)
        mock_configure_logging.assert_called_once()
        mock_initialize_database.assert_called_once_with(logger=logger)
        mock_load_settings.assert_called_once_with()
        mock_import_webview.assert_called_once_with()
        logger.error.assert_called_once_with("Startup aborted: %s", "pywebview is not installed")


if __name__ == "__main__":
    unittest.main()
