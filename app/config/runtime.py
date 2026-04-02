"""Runtime defaults and limits for the assistant."""

from app.config.llm import DEFAULT_LLM_MODEL
from app.speech.wake_word import DEFAULT_WAKE_PHRASES

BOT_NAME = "Maki"

VOICE_TIMEOUT_SECONDS = 5
VOICE_PHRASE_LIMIT_SECONDS = 8
MIN_VOICE_TIMEOUT_SECONDS = 1
MAX_VOICE_TIMEOUT_SECONDS = 30
MIN_VOICE_PHRASE_LIMIT_SECONDS = 1
MAX_VOICE_PHRASE_LIMIT_SECONDS = 30

DEFAULT_LLM_TIMEOUT_SECONDS = 15
MIN_LLM_TIMEOUT_SECONDS = 1
MAX_LLM_TIMEOUT_SECONDS = 60

DEFAULT_HISTORY_LIMIT = 100
MAX_HISTORY_LIMIT = 1000

DEFAULT_SETTINGS: dict[str, object] = {
    "bot_name": BOT_NAME,
    "speech_input_enabled": True,
    "speech_output_enabled": True,
    "tts_backend": "auto",
    "tts_voice_name": "",
    "tts_rate": 0,
    "tts_volume": 100,
    "microphone_index": None,
    "voice_timeout_seconds": VOICE_TIMEOUT_SECONDS,
    "voice_phrase_limit_seconds": VOICE_PHRASE_LIMIT_SECONDS,
    "wake_word_enabled": False,
    "wake_phrases": list(DEFAULT_WAKE_PHRASES),
    "require_confirmation": True,
    "console_fallback_enabled": True,
    "conversation_mode_enabled": True,
    "always_voice_responses": True,
    "typing_live_mode": False,
    "history_limit": DEFAULT_HISTORY_LIMIT,
    "allow_system_commands": False,
    "open_browser_enabled": True,
    "llm_parser_enabled": None,
    "llm_provider": "auto",
    "llm_model": DEFAULT_LLM_MODEL,
    "llm_timeout_seconds": DEFAULT_LLM_TIMEOUT_SECONDS,
}
