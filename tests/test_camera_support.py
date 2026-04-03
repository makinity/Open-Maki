"""Tests for screenshot, camera capture, and app close support."""

import subprocess
import unittest
from unittest.mock import MagicMock, patch

from app.actions.apps import close_app, open_app, take_picture, take_screenshot
from app.brain.command_router import route_command
from app.brain.intent_parser import parse_intent
from app.models.app_aliases import BUILTIN_APP_ENTRIES


class MediaSupportTests(unittest.TestCase):
    """Verify screenshot, camera capture, and app close support."""

    @patch("app.brain.intent_parser.load_command_patterns", return_value=[])
    @patch("app.brain.intent_parser.load_website_aliases", return_value={})
    def test_parse_take_picture_intent_uses_default_patterns(
        self,
        mock_load_website_aliases,
        mock_load_command_patterns,
    ) -> None:
        """The rule parser should detect built-in take-picture phrases."""
        intent = parse_intent("take a picture")

        self.assertEqual(
            intent,
            {
                "intent": "take_picture",
                "target": "",
                "raw_text": "take a picture",
            },
        )
        mock_load_command_patterns.assert_called_once_with()
        mock_load_website_aliases.assert_called_once_with()

    @patch("app.brain.intent_parser.load_command_patterns", return_value=[])
    @patch("app.brain.intent_parser.load_website_aliases", return_value={})
    def test_parse_take_screenshot_intent_uses_default_patterns(
        self,
        mock_load_website_aliases,
        mock_load_command_patterns,
    ) -> None:
        """The rule parser should detect built-in screenshot phrases."""
        intent = parse_intent("take a screenshot")

        self.assertEqual(
            intent,
            {
                "intent": "take_screenshot",
                "target": "",
                "raw_text": "take a screenshot",
            },
        )
        mock_load_command_patterns.assert_called_once_with()
        mock_load_website_aliases.assert_called_once_with()

    @patch("app.brain.intent_parser.load_command_patterns", return_value=[])
    @patch("app.brain.intent_parser.load_website_aliases", return_value={})
    def test_parse_close_app_intent_uses_default_patterns(
        self,
        mock_load_website_aliases,
        mock_load_command_patterns,
    ) -> None:
        """The rule parser should detect built-in close-app phrases."""
        intent = parse_intent("close camera")

        self.assertEqual(
            intent,
            {
                "intent": "close_app",
                "target": "camera",
                "raw_text": "close camera",
            },
        )
        mock_load_command_patterns.assert_called_once_with()
        mock_load_website_aliases.assert_called_once_with()

    def test_builtin_app_entries_include_camera_alias(self) -> None:
        """The built-in app alias list should include a Windows camera entry."""
        camera_entry = next(entry for entry in BUILTIN_APP_ENTRIES if entry["name"] == "camera")

        self.assertEqual(camera_entry["command"], "microsoft.windows.camera:")
        self.assertIn("camera", camera_entry["aliases"])
        self.assertIn("webcam", camera_entry["aliases"])

    @patch("app.actions.apps.os.startfile", create=True)
    def test_open_app_supports_windows_camera_protocol_alias(self, mock_startfile) -> None:
        """Opening the camera alias should use the Windows shell protocol target."""
        with patch("app.actions.apps.os.name", "nt"):
            result = open_app(
                "camera",
                app_registry={
                    "apps": {
                        "camera": {
                            "name": "camera",
                            "command": "microsoft.windows.camera:",
                        }
                    },
                    "folders": {},
                },
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "Opening camera.")
        mock_startfile.assert_called_once_with("microsoft.windows.camera:")

    @patch("app.actions.apps.subprocess.run")
    def test_close_app_supports_windows_camera_process_alias(self, mock_run) -> None:
        """Closing the camera alias should target the known Windows camera process."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["taskkill"],
            returncode=0,
            stdout="SUCCESS",
            stderr="",
        )

        with patch("app.actions.apps.os.name", "nt"):
            result = close_app(
                "camera",
                app_registry={
                    "apps": {
                        "camera": {
                            "name": "camera",
                            "command": "microsoft.windows.camera:",
                        }
                    },
                    "folders": {},
                },
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "Closing camera.")
        mock_run.assert_called_once_with(
            ["taskkill", "/IM", "WindowsCamera.exe", "/T", "/F"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
            check=False,
        )

    @patch("app.actions.apps.subprocess.run")
    def test_close_app_infers_process_name_for_standard_aliases(self, mock_run) -> None:
        """Closing a normal alias should infer its process name from the command when possible."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["taskkill"],
            returncode=0,
            stdout="SUCCESS",
            stderr="",
        )

        with patch("app.actions.apps.os.name", "nt"):
            result = close_app(
                "chrome",
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
        self.assertEqual(result["message"], "Closing chrome.")
        mock_run.assert_called_once_with(
            ["taskkill", "/IM", "chrome.exe", "/T", "/F"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
            check=False,
        )

    @patch("app.actions.apps.cv2", None)
    def test_take_picture_reports_missing_optional_dependency(self) -> None:
        """Photo capture should fail cleanly when OpenCV is not installed."""
        result = take_picture()

        self.assertFalse(result["success"])
        self.assertEqual(result["data"]["status"], "dependency_missing")
        self.assertIn("opencv-python", result["message"])

    @patch("app.actions.apps.mss", None)
    @patch("app.actions.apps.mss_tools", None)
    @patch("app.actions.apps.ImageGrab", None)
    @patch("app.actions.apps.pyautogui", None)
    def test_take_screenshot_reports_missing_optional_dependency(self) -> None:
        """Screenshot capture should fail cleanly when no screenshot backend is installed."""
        result = take_screenshot()

        self.assertFalse(result["success"])
        self.assertEqual(result["data"]["status"], "dependency_missing")
        self.assertIn("ImageGrab", result["message"])

    @patch("app.actions.apps.mss", None)
    @patch("app.actions.apps.mss_tools", None)
    def test_take_screenshot_falls_back_to_image_grab(self) -> None:
        """Screenshot capture should fall back to Pillow ImageGrab when mss is unavailable."""
        fake_image = MagicMock()
        with patch("app.actions.apps.ImageGrab") as mock_image_grab:
            mock_image_grab.grab.return_value = fake_image
            result = take_screenshot()

        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["status"], "completed")
        mock_image_grab.grab.assert_called_once_with()
        fake_image.save.assert_called_once()

    @patch("app.brain.llm_intent_parser.load_website_aliases", return_value={})
    @patch(
        "app.brain.llm_intent_parser.request_intent_tool_call",
        return_value={"name": "select_intent", "arguments": {"intent": "take_picture"}},
    )
    def test_llm_parser_normalizes_take_picture_without_target(
        self,
        mock_request_intent_tool_call,
        mock_load_website_aliases,
    ) -> None:
        """The optional LLM parser should normalize the targetless take-picture intent."""
        from app.brain.llm_intent_parser import parse_intent_with_llm

        intent = parse_intent_with_llm(
            "take a picture",
            settings={"llm_parser_enabled": True},
            app_registry={"apps": {}, "folders": {}},
        )

        self.assertEqual(
            intent,
            {
                "intent": "take_picture",
                "target": "",
                "raw_text": "take a picture",
            },
        )
        mock_request_intent_tool_call.assert_called_once()
        mock_load_website_aliases.assert_called_once_with()

    @patch("app.brain.llm_intent_parser.load_website_aliases", return_value={})
    @patch(
        "app.brain.llm_intent_parser.request_intent_tool_call",
        return_value={"name": "select_intent", "arguments": {"intent": "take_screenshot"}},
    )
    def test_llm_parser_normalizes_take_screenshot_without_target(
        self,
        mock_request_intent_tool_call,
        mock_load_website_aliases,
    ) -> None:
        """The optional LLM parser should normalize the targetless screenshot intent."""
        from app.brain.llm_intent_parser import parse_intent_with_llm

        intent = parse_intent_with_llm(
            "take a screenshot",
            settings={"llm_parser_enabled": True},
            app_registry={"apps": {}, "folders": {}},
        )

        self.assertEqual(
            intent,
            {
                "intent": "take_screenshot",
                "target": "",
                "raw_text": "take a screenshot",
            },
        )
        mock_request_intent_tool_call.assert_called_once()
        mock_load_website_aliases.assert_called_once_with()

    @patch("app.brain.llm_intent_parser.load_website_aliases", return_value={})
    @patch(
        "app.brain.llm_intent_parser.request_intent_tool_call",
        return_value={"name": "select_intent", "arguments": {"intent": "close_app", "target": "camera"}},
    )
    def test_llm_parser_normalizes_close_app_with_target(
        self,
        mock_request_intent_tool_call,
        mock_load_website_aliases,
    ) -> None:
        """The optional LLM parser should normalize the targeted close-app intent."""
        from app.brain.llm_intent_parser import parse_intent_with_llm

        intent = parse_intent_with_llm(
            "close camera",
            settings={"llm_parser_enabled": True},
            app_registry={"apps": {}, "folders": {}},
        )

        self.assertEqual(
            intent,
            {
                "intent": "close_app",
                "target": "camera",
                "raw_text": "close camera",
            },
        )
        mock_request_intent_tool_call.assert_called_once()
        mock_load_website_aliases.assert_called_once_with()

    @patch(
        "app.brain.command_router.take_picture",
        return_value={
            "success": True,
            "message": "I took a picture and saved it to public\\uploads\\camera\\photo_test.jpg.",
            "data": {
                "status": "completed",
                "path": "C:/Python/MakiBot/public/uploads/camera/photo_test.jpg",
            },
        },
    )
    def test_route_take_picture_dispatches_to_camera_action(self, mock_take_picture) -> None:
        """The command router should dispatch the take-picture intent."""
        result = route_command(
            {"intent": "take_picture", "target": "", "raw_text": "take a picture"},
            settings={"camera_device_index": 0},
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["status"], "completed")
        mock_take_picture.assert_called_once_with(settings={"camera_device_index": 0})

    @patch(
        "app.brain.command_router.take_screenshot",
        return_value={
            "success": True,
            "message": "I took a screenshot and saved it to public\\uploads\\screenshots\\screenshot_test.png.",
            "data": {
                "status": "completed",
                "path": "C:/Python/MakiBot/public/uploads/screenshots/screenshot_test.png",
            },
        },
    )
    def test_route_take_screenshot_dispatches_to_media_action(self, mock_take_screenshot) -> None:
        """The command router should dispatch the screenshot intent."""
        result = route_command(
            {"intent": "take_screenshot", "target": "", "raw_text": "take a screenshot"},
            settings={},
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["status"], "completed")
        mock_take_screenshot.assert_called_once_with(settings={})

    @patch(
        "app.brain.command_router.close_app",
        return_value={
            "success": True,
            "message": "Closing camera.",
            "data": {"status": "completed", "target": "camera"},
        },
    )
    def test_route_close_app_dispatches_to_app_action(self, mock_close_app) -> None:
        """The command router should dispatch the close-app intent."""
        result = route_command(
            {"intent": "close_app", "target": "camera", "raw_text": "close camera"},
            app_registry={"apps": {}, "folders": {}},
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["status"], "completed")
        mock_close_app.assert_called_once_with("camera", {"apps": {}, "folders": {}})


if __name__ == "__main__":
    unittest.main()

