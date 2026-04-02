"""Speech output module with console output and optional text-to-speech."""

from __future__ import annotations

import json
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

    if _try_windows_tts(text=text, settings=settings, tts_backend=tts_backend, logger=logger):
        return

    _reset_tts_engine()
    engine = _get_tts_engine(logger)
    if engine is None:
        _try_windows_tts(text=text, settings=settings, tts_backend="powershell", logger=logger)
        return

    _apply_pyttsx3_settings(engine, settings)

    try:
        engine.say(text)
        engine.runAndWait()
    except Exception as error:
        _reset_tts_engine(engine)
        _log_once(logger, f"Text-to-speech output failed: {error}", level="warning")
        _try_windows_tts(text=text, settings=settings, tts_backend="powershell", logger=logger)
        return

    _reset_tts_engine(engine)


def get_available_voices(logger: Any = None) -> list[dict[str, str]]:
    """Return the installed text-to-speech voices available on this machine."""
    voices = _get_pyttsx3_voices(logger)
    if voices:
        return voices

    if os.name == "nt":
        return _get_windows_voices(logger)

    return []


def _try_windows_tts(
    text: str,
    settings: dict[str, Any],
    tts_backend: str,
    logger: Any = None,
) -> bool:
    """Use the Windows speech synthesizer when the selected backend allows it."""
    if os.name != "nt":
        return False

    if tts_backend not in {"auto", "powershell", "windows"}:
        return False

    return _speak_with_powershell(text=text, settings=settings, logger=logger)


def _speak_with_powershell(
    text: str,
    settings: dict[str, Any],
    logger: Any = None,
) -> bool:
    """Speak one message using the built-in Windows speech synthesizer."""
    speech_script = (
        "Add-Type -AssemblyName System.Speech; "
        "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "if ($env:MAKI_TTS_VOICE_NAME) { try { $speaker.SelectVoice($env:MAKI_TTS_VOICE_NAME) } catch {} }; "
        "if ($env:MAKI_TTS_RATE) { $speaker.Rate = [int]$env:MAKI_TTS_RATE }; "
        "if ($env:MAKI_TTS_VOLUME) { $speaker.Volume = [int]$env:MAKI_TTS_VOLUME }; "
        "$speaker.Speak($env:MAKI_TTS_TEXT)"
    )
    environment = os.environ.copy()
    environment["MAKI_TTS_TEXT"] = text
    environment["MAKI_TTS_VOICE_NAME"] = str(settings.get("tts_voice_name", "")).strip()
    environment["MAKI_TTS_RATE"] = str(_coerce_int(settings.get("tts_rate"), default=0, minimum=-10, maximum=10))
    environment["MAKI_TTS_VOLUME"] = str(
        _coerce_int(settings.get("tts_volume"), default=100, minimum=0, maximum=100)
    )

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


def _reset_tts_engine(engine: Any | None = None) -> None:
    """Stop and clear the cached text-to-speech engine."""
    global _TTS_ENGINE

    active_engine = engine if engine is not None else _TTS_ENGINE
    if active_engine is not None:
        try:
            active_engine.stop()
        except Exception:
            pass

    _TTS_ENGINE = None


def _apply_pyttsx3_settings(engine: Any, settings: dict[str, Any]) -> None:
    """Apply the currently configured voice, rate, and volume to pyttsx3."""
    requested_voice = str(settings.get("tts_voice_name", "")).strip().lower()
    if requested_voice:
        for voice in engine.getProperty("voices") or []:
            voice_name = str(getattr(voice, "name", "")).strip().lower()
            voice_id = str(getattr(voice, "id", "")).strip().lower()
            if requested_voice in {voice_name, voice_id}:
                engine.setProperty("voice", getattr(voice, "id", ""))
                break

    relative_rate = _coerce_int(settings.get("tts_rate"), default=0, minimum=-10, maximum=10)
    engine.setProperty("rate", 200 + (relative_rate * 15))

    volume_percent = _coerce_int(settings.get("tts_volume"), default=100, minimum=0, maximum=100)
    engine.setProperty("volume", volume_percent / 100)


def _get_pyttsx3_voices(logger: Any = None) -> list[dict[str, str]]:
    """Return normalized voice metadata from pyttsx3 when available."""
    engine = _get_tts_engine(logger)
    if engine is None:
        return []

    voices: list[dict[str, str]] = []
    for voice in engine.getProperty("voices") or []:
        normalized_voice = {
            "id": str(getattr(voice, "id", "")).strip(),
            "name": str(getattr(voice, "name", "")).strip() or "Unknown voice",
            "languages": _normalize_languages(getattr(voice, "languages", None)),
            "gender": str(getattr(voice, "gender", "")).strip(),
            "age": str(getattr(voice, "age", "")).strip(),
        }
        voices.append(normalized_voice)

    return voices


def _get_windows_voices(logger: Any = None) -> list[dict[str, str]]:
    """Return normalized voice metadata from the Windows speech synthesizer."""
    voice_script = (
        "Add-Type -AssemblyName System.Speech; "
        "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$voices = $speaker.GetInstalledVoices() | ForEach-Object { "
        "  $info = $_.VoiceInfo; "
        "  [PSCustomObject]@{ "
        "    id = $info.Id; "
        "    name = $info.Name; "
        "    languages = ($info.Culture.Name); "
        "    gender = $info.Gender.ToString(); "
        "    age = $info.Age.ToString() "
        "  } "
        "}; "
        "$voices | ConvertTo-Json -Compress"
    )

    try:
        completed_process = subprocess.run(
            ["powershell", "-NoProfile", "-Command", voice_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            check=False,
        )
    except Exception as error:
        _log_once(logger, f"Unable to list Windows speech voices: {error}", level="warning")
        return []

    if completed_process.returncode != 0:
        error_message = (completed_process.stderr or "").strip() or "Unknown PowerShell voice query error."
        _log_once(logger, f"Unable to list Windows speech voices: {error_message}", level="warning")
        return []

    try:
        data = json.loads((completed_process.stdout or "").strip() or "[]")
    except json.JSONDecodeError:
        return []

    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return []

    voices: list[dict[str, str]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        voices.append(
            {
                "id": str(item.get("id", "")).strip(),
                "name": str(item.get("name", "")).strip() or "Unknown voice",
                "languages": str(item.get("languages", "")).strip(),
                "gender": str(item.get("gender", "")).strip(),
                "age": str(item.get("age", "")).strip(),
            }
        )
    return voices


def _normalize_languages(raw_languages: Any) -> str:
    """Return a readable language string from pyttsx3 voice metadata."""
    if raw_languages is None:
        return ""

    values = raw_languages if isinstance(raw_languages, (list, tuple)) else [raw_languages]
    cleaned_values: list[str] = []
    for value in values:
        if isinstance(value, bytes):
            decoded_value = value.decode("utf-8", errors="ignore")
        else:
            decoded_value = str(value)

        normalized_value = decoded_value.strip().strip("[]'\"")
        if normalized_value and normalized_value not in cleaned_values:
            cleaned_values.append(normalized_value)

    return ", ".join(cleaned_values)


def _coerce_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    """Convert a value into a bounded integer using a safe fallback."""
    try:
        parsed_value = int(value)
    except (TypeError, ValueError):
        return default

    return max(minimum, min(maximum, parsed_value))


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


# TODO: Add pitch control when the selected speech backend supports it cleanly.
