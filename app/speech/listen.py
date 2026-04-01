"""Speech input module with microphone support and console fallback."""

from __future__ import annotations

from typing import Any

from app.config import VOICE_PHRASE_LIMIT_SECONDS, VOICE_TIMEOUT_SECONDS
from app.speech.wake_word import DEFAULT_WAKE_PHRASES, detect_wake_phrase
from app.utils.helpers import normalize_text

try:
    import speech_recognition as sr
except ImportError:
    sr = None

_VOICE_INPUT_DISABLED = False
_VOICE_WARNING_MESSAGES: set[str] = set()
_WAKE_WORD_VOICE_ATTEMPTS = 1
_AMBIENT_NOISE_ADJUST_SECONDS = 0.3
_WAKE_WORD_BYPASS_INPUTS = {
    "exit",
    "exit bot",
    "quit",
    "quit bot",
    "bye",
    "goodbye",
}


def listen(
    settings: dict[str, Any] | None = None,
    logger: Any = None,
) -> dict[str, object]:
    """Capture one command from voice input or fall back to the console."""
    settings = settings or {}
    speech_input_enabled = bool(
        settings.get("speech_input_enabled", settings.get("voice_enabled", True))
    )
    allow_console_fallback = bool(settings.get("console_fallback_enabled", True))
    wake_word_enabled = bool(settings.get("wake_word_enabled", False))
    wake_phrases = settings.get("wake_phrases", DEFAULT_WAKE_PHRASES)
    microphone_index = _coerce_optional_int(settings.get("microphone_index"))

    voice_timeout = _coerce_positive_int(
        settings.get("voice_timeout_seconds", VOICE_TIMEOUT_SECONDS),
        default=VOICE_TIMEOUT_SECONDS,
    )
    phrase_limit = _coerce_positive_int(
        settings.get("voice_phrase_limit_seconds", VOICE_PHRASE_LIMIT_SECONDS),
        default=VOICE_PHRASE_LIMIT_SECONDS,
    )

    if speech_input_enabled and not _VOICE_INPUT_DISABLED:
        voice_attempts = _WAKE_WORD_VOICE_ATTEMPTS if wake_word_enabled else 1
        last_voice_status = "empty"

        for _ in range(voice_attempts):
            voice_result = _listen_from_microphone(
                microphone_index=microphone_index,
                timeout_seconds=voice_timeout,
                phrase_limit_seconds=phrase_limit,
                logger=logger,
            )
            spoken_text = str(voice_result.get("text", ""))
            voice_status = str(voice_result.get("status", "ok"))
            last_voice_status = voice_status

            if spoken_text:
                return _build_wake_word_payload(
                    spoken_text,
                    source="voice",
                    used_fallback=False,
                    wake_word_enabled=wake_word_enabled,
                    wake_phrases=wake_phrases,
                    logger=logger,
                )

            if wake_word_enabled and voice_status in {"voice_timeout", "voice_unrecognized"}:
                continue

            break

        if wake_word_enabled and last_voice_status in {"voice_timeout", "voice_unrecognized"}:
            return _build_payload(
                "",
                source="voice",
                used_fallback=False,
                status=last_voice_status,
            )

    if allow_console_fallback:
        used_fallback = speech_input_enabled
        return _listen_from_console(
            used_fallback=used_fallback,
            settings=settings,
            logger=logger,
        )

    return _build_payload("", source="none", used_fallback=False, status="empty")


def _listen_from_microphone(
    microphone_index: int | None,
    timeout_seconds: int,
    phrase_limit_seconds: int,
    logger: Any = None,
) -> dict[str, str]:
    """Listen for a single spoken phrase and convert it to text."""
    if sr is None:
        _disable_voice_input(
            "SpeechRecognition is not installed. Using console input instead.",
            logger,
        )
        return {"text": "", "status": "voice_unavailable"}

    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 1.0
    recognizer.non_speaking_duration = 0.5
    recognizer.phrase_threshold = 0.2

    try:
        microphone_name = _get_microphone_name(microphone_index)
        if microphone_name:
            _log_info(logger, f"Listening for voice input on '{microphone_name}'.")
        else:
            _log_info(logger, "Listening for voice input.")

        with _open_microphone(microphone_index) as source:
            recognizer.adjust_for_ambient_noise(
                source,
                duration=_AMBIENT_NOISE_ADJUST_SECONDS,
            )
            audio = recognizer.listen(
                source,
                timeout=timeout_seconds,
                phrase_time_limit=phrase_limit_seconds,
            )

        heard_text = recognizer.recognize_google(audio)
        normalized_text = normalize_text(heard_text)
        _log_info(logger, f"Heard: {normalized_text}")
        return {"text": normalized_text, "status": "ok"}

    except _get_sr_exception("UnknownValueError"):
        _log_info(logger, "Speech was detected but could not be understood.")
        return {"text": "", "status": "voice_unrecognized"}
    except _get_sr_exception("WaitTimeoutError"):
        _log_info(logger, "No speech was detected before the timeout.")
        return {"text": "", "status": "voice_timeout"}
    except _get_sr_exception("RequestError") as error:
        _log_info(logger, f"Speech recognition request failed: {error}")
        return {"text": "", "status": "voice_request_error"}
    except Exception as error:
        _disable_voice_input(
            f"Voice input is unavailable in this session. Falling back to console. {error}",
            logger,
        )
        return {"text": "", "status": "voice_unavailable"}


def _listen_from_console(
    used_fallback: bool,
    settings: dict[str, Any] | None = None,
    logger: Any = None,
) -> dict[str, object]:
    """Read a command from standard input as a reliable fallback."""
    settings = settings or {}
    wake_word_enabled = bool(settings.get("wake_word_enabled", False))
    console_wake_word_optional = bool(settings.get("console_wake_word_optional", False))
    wake_phrases = settings.get("wake_phrases", DEFAULT_WAKE_PHRASES)

    try:
        text = normalize_text(input("You: "))
    except (EOFError, KeyboardInterrupt):
        text = "exit"

    return _build_wake_word_payload(
        text,
        source="console",
        used_fallback=used_fallback,
        wake_word_enabled=wake_word_enabled,
        wake_phrases=wake_phrases,
        wake_word_optional=console_wake_word_optional,
        logger=logger,
    )


def _build_wake_word_payload(
    text: str,
    source: str,
    used_fallback: bool,
    wake_word_enabled: bool,
    wake_phrases: list[str] | None,
    wake_word_optional: bool = False,
    logger: Any = None,
) -> dict[str, object]:
    """Apply optional wake-word parsing to a captured input string."""
    if not wake_word_enabled:
        return _build_payload(text, source=source, used_fallback=used_fallback)

    normalized_text = normalize_text(text).lower()
    if normalized_text in _WAKE_WORD_BYPASS_INPUTS:
        return _build_payload(text, source=source, used_fallback=used_fallback)

    matched, command_text = detect_wake_phrase(text, wake_phrases)
    if not matched:
        if wake_word_optional:
            return _build_payload(
                text,
                source=source,
                used_fallback=used_fallback,
            )

        _log_debug(logger, f"Ignoring {source} input without wake word: {text}")
        return _build_payload(
            "",
            source=source,
            used_fallback=used_fallback,
            status="missing_wake_word",
        )

    if not command_text:
        return _build_payload(
            "",
            source=source,
            used_fallback=used_fallback,
            status="wake_word_only",
        )

    return _build_payload(command_text, source=source, used_fallback=used_fallback)


def _build_payload(
    text: str,
    source: str,
    used_fallback: bool,
    status: str = "ok",
) -> dict[str, object]:
    """Return the consistent input payload structure used by the assistant."""
    return {
        "text": normalize_text(text),
        "source": source,
        "used_fallback": used_fallback,
        "status": status,
    }


def _disable_voice_input(message: str, logger: Any = None) -> None:
    """Disable voice input for the current session after a hard failure."""
    global _VOICE_INPUT_DISABLED

    _VOICE_INPUT_DISABLED = True
    _log_once(logger, message, level="warning")


def _get_sr_exception(name: str) -> type[Exception]:
    """Return a SpeechRecognition exception class or a safe fallback."""
    if sr is None:
        return Exception

    exception_type = getattr(sr, name, Exception)
    if isinstance(exception_type, type) and issubclass(exception_type, Exception):
        return exception_type

    return Exception


def _open_microphone(microphone_index: int | None) -> Any:
    """Return a microphone instance using the selected device when provided."""
    if sr is None:
        raise RuntimeError("SpeechRecognition is not installed.")

    if microphone_index is None:
        return sr.Microphone()

    return sr.Microphone(device_index=microphone_index)


def _get_microphone_name(microphone_index: int | None) -> str:
    """Return the friendly microphone name for a selected device index."""
    if sr is None or microphone_index is None:
        return ""

    try:
        microphone_names = sr.Microphone.list_microphone_names()
    except Exception:
        return ""

    if 0 <= microphone_index < len(microphone_names):
        return str(microphone_names[microphone_index])

    return ""


def _coerce_positive_int(value: Any, default: int) -> int:
    """Return a positive integer value using a safe default on invalid input."""
    try:
        parsed_value = int(value)
    except (TypeError, ValueError):
        return default

    return parsed_value if parsed_value > 0 else default


def _coerce_optional_int(value: Any) -> int | None:
    """Convert a value into an integer or return None when it is unset."""
    if value is None:
        return None

    if isinstance(value, str) and not value.strip():
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _log_debug(logger: Any, message: str) -> None:
    """Log a debug message when a logger is available."""
    if logger is not None:
        logger.debug(message)


def _log_info(logger: Any, message: str) -> None:
    """Log an informational message when a logger is available."""
    if logger is not None:
        logger.info(message)


def _log_once(logger: Any, message: str, level: str = "warning") -> None:
    """Log a message once for the current Python process."""
    if message in _VOICE_WARNING_MESSAGES:
        return

    _VOICE_WARNING_MESSAGES.add(message)

    if logger is None:
        return

    log_method = getattr(logger, level, logger.warning)
    log_method(message)
