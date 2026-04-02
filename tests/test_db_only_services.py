"""Tests for DB-only app registry and history services."""

import unittest
from unittest.mock import patch

from app.services.app_registry import load_app_registry
from app.services.history_service import add_history_entry, load_history


class DbOnlyServiceTests(unittest.TestCase):
    """Verify that runtime storage services now rely on MySQL only."""

    @patch("app.services.app_registry.load_folder_alias_entries")
    @patch("app.services.app_registry.load_app_alias_entries")
    @patch("app.services.app_registry.ensure_database_ready")
    def test_load_app_registry_uses_database_entries_only(
        self,
        mock_ensure_database_ready,
        mock_load_app_alias_entries,
        mock_load_folder_alias_entries,
    ) -> None:
        """App registry should be assembled from MySQL alias rows."""
        mock_load_app_alias_entries.return_value = [
            {"alias": "chrome", "name": "Google Chrome", "command": ["chrome"]}
        ]
        mock_load_folder_alias_entries.return_value = [
            {"alias": "downloads", "name": "Downloads", "path": "C:/Users/Maki/Downloads"}
        ]

        registry = load_app_registry()

        self.assertEqual(registry["apps"]["chrome"]["name"], "Google Chrome")
        self.assertEqual(registry["apps"]["chrome"]["command"], ["chrome"])
        self.assertEqual(
            registry["folders"]["downloads"]["path"],
            "C:\\Users\\Maki\\Downloads",
        )
        mock_ensure_database_ready.assert_called_once()

    @patch("app.services.history_service.load_history_entries")
    @patch("app.services.history_service.ensure_database_ready")
    def test_load_history_uses_database_only(
        self,
        mock_ensure_database_ready,
        mock_load_history_entries,
    ) -> None:
        """History loading should delegate directly to MySQL storage."""
        mock_load_history_entries.return_value = [{"raw_text": "open chrome"}]

        history = load_history()

        self.assertEqual(history, [{"raw_text": "open chrome"}])
        mock_ensure_database_ready.assert_called_once()
        mock_load_history_entries.assert_called_once_with()

    @patch("app.services.history_service.insert_history_entry")
    @patch("app.services.history_service.ensure_database_ready")
    def test_add_history_entry_writes_directly_to_database(
        self,
        mock_ensure_database_ready,
        mock_insert_history_entry,
    ) -> None:
        """History writes should insert rows into MySQL when no trim limit is used."""
        result = add_history_entry(
            command_text="help",
            intent={"intent": "help", "target": "", "raw_text": "help"},
            result={"success": True, "message": "Sure.", "data": {"status": "completed"}},
            history_limit=0,
            source="console",
        )

        self.assertEqual(result["intent"], "help")
        self.assertEqual(result["source"], "console")
        mock_ensure_database_ready.assert_called_once()
        mock_insert_history_entry.assert_called_once_with(result)


if __name__ == "__main__":
    unittest.main()
