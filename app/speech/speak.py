"""Speech output module with console output and optional text-to-speech."""

import os
import subprocess
from typing import Any

from app.config import BOT_NAME

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

_TTS_ENGINE: Any | None = None
_TTS_DISABLED = False
_TTS_WARNING_MESSAGES: set[str] = set()


def speak(
    text: str,
    settings: dict[str, Any] | None = None,
    logger: Any = None,
    use_tts: bool = True,
) -> None:
    """Print assistant output and speak it aloud when TTS is available."""
    settings = settings or {}
    bot_name = str(settings.get("bot_name", BOT_NAME))
    speech_output_enabled = bool(
        settings.get("speech_output_enabled", settings.get("voice_enabled", True))
    )
    tts_backend = str(settings.get("tts_backend", "auto")).strip().lower() or "auto"

    print(f"{bot_name}: {text}")

    if not speech_output_enabled or not use_tts:
        return

    if _try_windows_tts(text=text, tts_backend=tts_backend, logger=logger):
        return

    engine = _get_tts_engine(logger)
    if engine is None:
        _try_windows_tts(text=text, tts_backend="powershell", logger=logger)
        return

    try:
        engine.say(text)
        engine.runAndWait()
    except Exception as error:
        _log_once(logger, f"Text-to-speech output failed: {error}", level="warning")
        _try_windows_tts(text=text, tts_backend="powershell", logger=logger)


def _try_windows_tts(text: str, tts_backend: str, logger: Any = None) -> bool:
    """Use the Windows speech synthesizer when the selected backend allows it."""
    if os.name != "nt":
        return False

    if tts_backend not in {"auto", "powershell", "windows"}:
        return False

    return _speak_with_powershell(text, logger)


def _speak_with_powershell(text: str, logger: Any = None) -> bool:
    """Speak one message using the built-in Windows speech synthesizer."""
    speech_script = (
        "Add-Type -AssemblyName System.Speech; "
        "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$speaker.Speak($env:MAKI_TTS_TEXT)"
    )
    environment = os.environ.copy()
    environment["MAKI_TTS_TEXT"] = text

    try:
        completed_process = subprocess.run(
            ["powershell", "-NoProfile", "-Command", speech_script],
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            check=False,
        )
    except Exception as error:
        _log_once(logger, f"Windows speech backend is unavailable: {error}", level="warning")
        return False

    if completed_process.returncode != 0:
        error_message = (completed_process.stderr or "").strip() or "Unknown PowerShell TTS error."
        _log_once(logger, f"Windows speech backend failed: {error_message}", level="warning")
        return False

    return True


def _get_tts_engine(logger: Any = None) -> Any | None:
    """Create and cache the text-to-speech engine when available."""
    global _TTS_ENGINE, _TTS_DISABLED

    if _TTS_DISABLED:
        return None

    if _TTS_ENGINE is not None:
        return _TTS_ENGINE

    if pyttsx3 is None:
        _TTS_DISABLED = True
        _log_once(logger, "pyttsx3 is not installed. Speech output is disabled.", level="warning")
        return None

    try:
        _TTS_ENGINE = pyttsx3.init()
        return _TTS_ENGINE
    except Exception as error:
        _TTS_DISABLED = True
        _log_once(logger, f"Unable to initialize text-to-speech: {error}", level="warning")
        return None


def _log_debug(logger: Any, message: str) -> None:
    """Log a debug message when a logger is available."""
    if logger is not None:
        logger.debug(message)


def _log_once(logger: Any, message: str, level: str = "warning") -> None:
    """Log a message once for the current Python process."""
    if message in _TTS_WARNING_MESSAGES:
        return

    _TTS_WARNING_MESSAGES.add(message)
    if logger is None:
        return

    log_method = getattr(logger, level, logger.warning)
    log_method(message)


# TODO: Add configurable voice selection and speech rate settings.
