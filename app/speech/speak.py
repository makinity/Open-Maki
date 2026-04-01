"""Speech output module with console output and optional text-to-speech."""

from typing import Any

from app.config import BOT_NAME

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

_TTS_ENGINE: Any | None = None
_TTS_DISABLED = False


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

    print(f"{bot_name}: {text}")

    if not speech_output_enabled or not use_tts:
        return

    engine = _get_tts_engine(logger)
    if engine is None:
        return

    try:
        engine.say(text)
        engine.runAndWait()
    except Exception as error:
        _log_debug(logger, f"Text-to-speech output failed: {error}")


def _get_tts_engine(logger: Any = None) -> Any | None:
    """Create and cache the text-to-speech engine when available."""
    global _TTS_ENGINE, _TTS_DISABLED

    if _TTS_DISABLED:
        return None

    if _TTS_ENGINE is not None:
        return _TTS_ENGINE

    if pyttsx3 is None:
        _TTS_DISABLED = True
        _log_debug(logger, "pyttsx3 is not installed. Speech output is disabled.")
        return None

    try:
        _TTS_ENGINE = pyttsx3.init()
        return _TTS_ENGINE
    except Exception as error:
        _TTS_DISABLED = True
        _log_debug(logger, f"Unable to initialize text-to-speech: {error}")
        return None


def _log_debug(logger: Any, message: str) -> None:
    """Log a debug message when a logger is available."""
    if logger is not None:
        logger.debug(message)


# TODO: Add configurable voice selection and speech rate settings.
