"""Tests for speech input and output helpers."""

from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

import app.speech.listen as listen_module
import app.speech.speak as speak_module


class _FakeUnknownValueError(Exception):
    """Fake speech recognition unknown-value error."""


class _FakeWaitTimeoutError(Exception):
    """Fake speech recognition timeout error."""


class _FakeRequestError(Exception):
    """Fake speech recognition request error."""


class _FakeMicrophone:
    """Simple context manager that mimics a microphone source."""

    def __enter__(self) -> object:
        return object()

    def __exit__(self, exc_type, exc, traceback) -> bool:
        return False


class _SuccessfulRecognizer:
    """Recognizer stub that returns a fixed phrase."""

    def adjust_for_ambient_noise(self, source: object, duration: float = 0.5) -> None:
        """Accept the ambient-noise calibration call."""

    def listen(self, source: object, timeout: int, phrase_time_limit: int) -> str:
        """Return fake audio data."""
        return "fake-audio"

    def recognize_google(self, audio: str) -> str:
        """Return a normalized speech result."""
        return "hello maki"


class _UnrecognizedRecognizer:
    """Recognizer stub that hears audio but cannot transcribe it."""

    def adjust_for_ambient_noise(self, source: object, duration: float = 0.5) -> None:
        """Accept the ambient-noise calibration call."""

    def listen(self, source: object, timeout: int, phrase_time_limit: int) -> str:
        """Return fake audio data."""
        return "fake-audio"

    def recognize_google(self, audio: str) -> str:
        """Raise the same error SpeechRecognition uses for unknown speech."""
        raise _FakeUnknownValueError()


class SpeechModuleTests(unittest.TestCase):
    """Verify voice input fallback behavior and safe speech output."""

    def test_listen_returns_voice_payload_when_microphone_succeeds(self) -> None:
        """A successful microphone turn should return a voice payload."""
        fake_sr = _build_fake_sr(_SuccessfulRecognizer)

        with patch.object(listen_module, "sr", fake_sr), patch.object(
            listen_module, "_VOICE_INPUT_DISABLED", False
        ), patch.object(listen_module, "_VOICE_WARNING_MESSAGES", set()):
            payload = listen_module.listen(
                settings={
                    "speech_input_enabled": True,
                    "console_fallback_enabled": True,
                    "voice_timeout_seconds": 2,
                    "voice_phrase_limit_seconds": 4,
                }
            )

        self.assertEqual(
            payload,
            {
                "text": "hello maki",
                "source": "voice",
                "used_fallback": False,
                "status": "ok",
            },
        )

    def test_listen_marks_wake_word_only_when_no_command_follows(self) -> None:
        """A bare wake phrase should be classified separately from empty input."""
        with patch("builtins.input", return_value="hey maki"):
            payload = listen_module.listen(
                settings={
                    "speech_input_enabled": False,
                    "console_fallback_enabled": True,
                    "wake_word_enabled": True,
                    "wake_phrases": ["hey maki"],
                }
            )

        self.assertEqual(
            payload,
            {
                "text": "",
                "source": "console",
                "used_fallback": False,
                "status": "wake_word_only",
            },
        )

    def test_listen_keeps_voice_mode_on_unrecognized_audio_in_wake_word_mode(self) -> None:
        """Wake-word mode should not drop straight to console on stray audio."""
        fake_sr = _build_fake_sr(_UnrecognizedRecognizer)

        with patch.object(listen_module, "sr", fake_sr), patch.object(
            listen_module, "_VOICE_INPUT_DISABLED", False
        ), patch.object(listen_module, "_VOICE_WARNING_MESSAGES", set()), patch(
            "builtins.input"
        ) as mock_input:
            payload = listen_module.listen(
                settings={
                    "speech_input_enabled": True,
                    "console_fallback_enabled": True,
                    "wake_word_enabled": True,
                    "wake_phrases": ["hey maki"],
                }
            )

        self.assertEqual(
            payload,
            {
                "text": "",
                "source": "voice",
                "used_fallback": False,
                "status": "voice_unrecognized",
            },
        )
        mock_input.assert_not_called()

    def test_listen_allows_exit_without_wake_phrase_in_console_fallback(self) -> None:
        """Exit should stay usable even when wake-word mode is enabled."""
        with patch("builtins.input", return_value="exit"):
            payload = listen_module.listen(
                settings={
                    "speech_input_enabled": False,
                    "console_fallback_enabled": True,
                    "wake_word_enabled": True,
                    "wake_phrases": ["hey maki"],
                }
            )

        self.assertEqual(
            payload,
            {
                "text": "exit",
                "source": "console",
                "used_fallback": False,
                "status": "ok",
            },
        )

    def test_listen_allows_plain_typed_commands_when_console_wake_word_is_optional(self) -> None:
        """Console fallback should accept direct typed commands without a wake phrase."""
        with patch("builtins.input", return_value="open chrome"):
            payload = listen_module.listen(
                settings={
                    "speech_input_enabled": False,
                    "console_fallback_enabled": True,
                    "wake_word_enabled": True,
                    "console_wake_word_optional": True,
                    "wake_phrases": ["hey maki"],
                }
            )

        self.assertEqual(
            payload,
            {
                "text": "open chrome",
                "source": "console",
                "used_fallback": False,
                "status": "ok",
            },
        )

    def test_listen_still_accepts_typed_wake_phrase_when_console_wake_word_is_optional(self) -> None:
        """Console fallback should still recognize a typed wake phrase when present."""
        with patch("builtins.input", return_value="hey maki"):
            payload = listen_module.listen(
                settings={
                    "speech_input_enabled": False,
                    "console_fallback_enabled": True,
                    "wake_word_enabled": True,
                    "console_wake_word_optional": True,
                    "wake_phrases": ["hey maki"],
                }
            )

        self.assertEqual(
            payload,
            {
                "text": "",
                "source": "console",
                "used_fallback": False,
                "status": "wake_word_only",
            },
        )

    def test_listen_falls_back_to_console_when_speech_recognition_is_missing(self) -> None:
        """Missing SpeechRecognition should not crash and should use console input."""
        with patch.object(listen_module, "sr", None), patch.object(
            listen_module, "_VOICE_INPUT_DISABLED", False
        ), patch.object(listen_module, "_VOICE_WARNING_MESSAGES", set()), patch(
            "builtins.input", return_value="typed fallback"
        ):
            payload = listen_module.listen(
                settings={
                    "speech_input_enabled": True,
                    "console_fallback_enabled": True,
                }
            )
            voice_disabled = listen_module._VOICE_INPUT_DISABLED

        self.assertEqual(payload["text"], "typed fallback")
        self.assertEqual(payload["source"], "console")
        self.assertTrue(payload["used_fallback"])
        self.assertEqual(payload["status"], "ok")
        self.assertTrue(voice_disabled)

    def test_speak_always_prints_even_when_speech_output_is_disabled(self) -> None:
        """Console output should remain available when TTS is turned off."""
        fake_pyttsx3 = MagicMock()

        with patch.object(speak_module, "pyttsx3", fake_pyttsx3), patch.object(
            speak_module, "_TTS_ENGINE", None
        ), patch.object(speak_module, "_TTS_DISABLED", False), patch(
            "builtins.print"
        ) as mock_print:
            speak_module.speak(
                "Hello there.",
                settings={
                    "bot_name": "Maki",
                    "speech_output_enabled": False,
                },
            )

        mock_print.assert_called_once_with("Maki: Hello there.")
        fake_pyttsx3.init.assert_not_called()

    def test_speak_handles_missing_tts_engine_without_crashing(self) -> None:
        """Missing pyttsx3 should still allow console output."""
        with patch.object(speak_module, "pyttsx3", None), patch.object(
            speak_module, "_TTS_ENGINE", None
        ), patch.object(speak_module, "_TTS_DISABLED", False), patch.object(
            speak_module, "_TTS_WARNING_MESSAGES", set()
        ), patch.object(
            speak_module.os, "name", "posix"
        ), patch(
            "builtins.print"
        ) as mock_print:
            speak_module.speak(
                "Speech fallback test.",
                settings={
                    "bot_name": "Maki",
                    "speech_output_enabled": True,
                },
            )
            tts_disabled = speak_module._TTS_DISABLED

        mock_print.assert_called_once_with("Maki: Speech fallback test.")
        self.assertTrue(tts_disabled)

    @patch.object(speak_module.os, "name", "nt")
    @patch("app.speech.speak.subprocess.run")
    def test_speak_uses_windows_backend_when_auto_mode_is_active(
        self,
        mock_subprocess_run,
    ) -> None:
        """Windows auto mode should prefer the PowerShell speech backend."""
        mock_subprocess_run.return_value = SimpleNamespace(returncode=0, stderr="")

        with patch.object(speak_module, "_TTS_WARNING_MESSAGES", set()), patch(
            "builtins.print"
        ) as mock_print:
            speak_module.speak(
                "Hello from Windows speech.",
                settings={
                    "bot_name": "Maki",
                    "speech_output_enabled": True,
                    "tts_backend": "auto",
                },
            )

        mock_print.assert_called_once_with("Maki: Hello from Windows speech.")
        mock_subprocess_run.assert_called_once()

    def test_speak_recreates_pyttsx3_engine_for_each_reply(self) -> None:
        """Repeated pyttsx3 replies should not reuse a stale cached engine."""
        first_engine = MagicMock()
        second_engine = MagicMock()
        fake_pyttsx3 = MagicMock()
        fake_pyttsx3.init.side_effect = [first_engine, second_engine]

        with patch.object(speak_module, "pyttsx3", fake_pyttsx3), patch.object(
            speak_module, "_TTS_ENGINE", None
        ), patch.object(speak_module, "_TTS_DISABLED", False), patch.object(
            speak_module.os, "name", "posix"
        ), patch(
            "builtins.print"
        ):
            speak_module.speak(
                "First reply.",
                settings={
                    "bot_name": "Maki",
                    "speech_output_enabled": True,
                    "tts_backend": "pyttsx3",
                },
            )
            speak_module.speak(
                "Second reply.",
                settings={
                    "bot_name": "Maki",
                    "speech_output_enabled": True,
                    "tts_backend": "pyttsx3",
                },
            )

        self.assertEqual(fake_pyttsx3.init.call_count, 2)
        first_engine.say.assert_called_once_with("First reply.")
        second_engine.say.assert_called_once_with("Second reply.")
        first_engine.stop.assert_called()
        second_engine.stop.assert_called()



def _build_fake_sr(recognizer_class: type[object]) -> SimpleNamespace:
    """Build a minimal speech_recognition replacement for tests."""
    return SimpleNamespace(
        Recognizer=recognizer_class,
        Microphone=_FakeMicrophone,
        UnknownValueError=_FakeUnknownValueError,
        WaitTimeoutError=_FakeWaitTimeoutError,
        RequestError=_FakeRequestError,
    )


# TODO: Add microphone hard-failure tests for missing audio devices.
if __name__ == "__main__":
    unittest.main()
