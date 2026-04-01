"""Assistant coordinator for input, parsing, routing, speaking, and history."""

from typing import Any

from app.brain.command_router import route_command
from app.brain.intent_parser import parse_intent
from app.config import BOT_NAME, DEFAULT_HISTORY_LIMIT
from app.services.app_registry import load_app_registry
from app.services.history_service import add_history_entry
from app.services.settings_service import load_settings
from app.speech.listen import listen
from app.speech.speak import speak
from app.utils.helpers import build_result, normalize_text
from app.utils.logger import get_logger

VALID_HISTORY_SOURCES = {"voice", "console", "system"}
VOICE_MISS_LIMIT_FOR_CONSOLE = 1


class MakiAssistant:
    """Run the main assistant workflow for one command or a full loop."""

    def __init__(self, settings: dict[str, Any] | None = None) -> None:
        """Create a new assistant with runtime settings and registry data."""
        self.logger = get_logger(self.__class__.__name__)
        self.settings = settings or load_settings()
        self.app_registry = load_app_registry()
        self.bot_name = str(self.settings.get("bot_name", BOT_NAME))
        self.history_limit = self._get_history_limit()
        self.pending_confirmation: dict[str, str] | None = None
        self.awaiting_followup_command = False
        self.consecutive_voice_misses = 0

    def run(self) -> None:
        """Start the assistant command loop until an exit command is received."""
        if bool(self.settings.get("wake_word_enabled", False)):
            self.say("Ready. Say 'hey maki' to wake me, or type a command.", use_tts=False)
        else:
            self.say("Ready. Say or type a command.", use_tts=False)

        while True:
            payload = listen(
                settings=self._build_listen_settings(),
                logger=self.logger,
            )
            text = normalize_text(str(payload.get("text", "")))
            source = self._normalize_source(str(payload.get("source", "none")))
            status = str(payload.get("status", "ok")).strip().lower()

            if status == "wake_word_only":
                self.consecutive_voice_misses = 0
                self.awaiting_followup_command = True
                self.say("I'm listening.", use_tts=False)
                continue

            if status == "missing_wake_word":
                self.consecutive_voice_misses = 0
                self.say(
                    "Please start with a wake phrase, like 'hey maki open chrome'.",
                    use_tts=False,
                )
                continue

            if status in {"voice_timeout", "voice_unrecognized"}:
                if self.awaiting_followup_command:
                    self.awaiting_followup_command = False
                    self.consecutive_voice_misses = 0
                    self.say("I didn't catch the follow-up command.", use_tts=False)
                    fallback_payload = self._capture_console_fallback(
                        "You can type the command instead."
                    )
                    if fallback_payload is None:
                        continue

                    text = normalize_text(str(fallback_payload.get("text", "")))
                    source = self._normalize_source(str(fallback_payload.get("source", "console")))
                    status = str(fallback_payload.get("status", "ok")).strip().lower()
                    if not text:
                        continue
                else:
                    self.consecutive_voice_misses += 1
                    if self.consecutive_voice_misses < VOICE_MISS_LIMIT_FOR_CONSOLE:
                        continue

                    self.consecutive_voice_misses = 0
                    fallback_payload = self._capture_console_fallback(
                        "Voice input is not catching anything. Type a command below, or press Enter to keep listening."
                    )
                    if fallback_payload is None:
                        continue

                    text = normalize_text(str(fallback_payload.get("text", "")))
                    source = self._normalize_source(str(fallback_payload.get("source", "console")))
                    status = str(fallback_payload.get("status", "ok")).strip().lower()
                    if not text:
                        continue

            if not text:
                if self.awaiting_followup_command:
                    self.awaiting_followup_command = False
                    self.say("I didn't catch the follow-up command.")
                    continue

                self.say("I did not receive a command.")
                continue

            self.awaiting_followup_command = False
            self.consecutive_voice_misses = 0
            result = self.handle_text(text, source=source)

            if result.get("message"):
                self.say(str(result["message"]))

            if bool((result.get("data") or {}).get("should_exit")):
                break

    def handle_text(self, text: str, source: str = "console") -> dict[str, Any]:
        """Parse raw user text, handle confirmations, and route the command."""
        normalized_source = self._normalize_source(source)
        intent = parse_intent(text)
        self.logger.info(
            "Command received from %s: %s",
            normalized_source,
            intent.get("raw_text", text),
        )

        result = self._handle_confirmation_state(intent)
        if result is None:
            result = route_command(
                intent,
                settings=self.settings,
                app_registry=self.app_registry,
                logger=self.logger,
            )
            self._update_pending_confirmation(intent, result)

        add_history_entry(
            command_text=text,
            intent=intent,
            result=result,
            history_limit=self.history_limit,
            source=normalized_source,
        )
        return result

    def say(self, message: str, use_tts: bool = True) -> None:
        """Send assistant output to the console and optional TTS."""
        speak(message, settings=self.settings, logger=self.logger, use_tts=use_tts)

    def _handle_confirmation_state(self, intent: dict[str, str]) -> dict[str, Any] | None:
        """Resolve any pending confirmation before routing a new command."""
        if self.pending_confirmation is None:
            if intent.get("intent") == "confirm_yes":
                return build_result(False, "There is no pending action to confirm.", {"status": "idle"})
            if intent.get("intent") == "confirm_no":
                return build_result(False, "There is no pending action to cancel.", {"status": "idle"})
            return None

        if intent.get("intent") == "confirm_yes":
            pending_intent = self.pending_confirmation
            self.pending_confirmation = None
            result = route_command(
                pending_intent,
                settings=self.settings,
                app_registry=self.app_registry,
                logger=self.logger,
                confirmed=True,
            )
            return self._prefix_result_message(
                result,
                "Confirmed.",
                extra_data={
                    "confirmed": True,
                    "confirmed_intent": pending_intent.get("intent", "unknown"),
                    "confirmed_target": pending_intent.get("target", ""),
                },
            )

        if intent.get("intent") == "confirm_no":
            pending_intent = self.pending_confirmation
            self.pending_confirmation = None
            return build_result(
                True,
                f"Canceled the pending {self._describe_pending_action(pending_intent)} request.",
                {
                    "status": "cancelled",
                    "confirmed": False,
                    "cancelled_intent": pending_intent.get("intent", "unknown"),
                    "cancelled_target": pending_intent.get("target", ""),
                },
            )

        pending_intent = self.pending_confirmation
        self.pending_confirmation = None
        self._record_system_history(
            pending_intent,
            build_result(
                True,
                f"Pending {self._describe_pending_action(pending_intent)} request canceled by a new command.",
                {"status": "auto_cancelled"},
            ),
        )
        return None

    def _update_pending_confirmation(
        self,
        intent: dict[str, str],
        result: dict[str, Any],
    ) -> None:
        """Store a pending confirmation request when required."""
        result_data = result.get("data") or {}
        if isinstance(result_data, dict) and result_data.get("requires_confirmation"):
            self.pending_confirmation = dict(intent)
            return

        if intent.get("intent") not in {"confirm_yes", "confirm_no"}:
            self.pending_confirmation = None

    def _record_system_history(self, intent: dict[str, str], result: dict[str, Any]) -> None:
        """Record assistant-generated events such as auto-cancelled confirmations."""
        add_history_entry(
            command_text=intent.get("raw_text", ""),
            intent=intent,
            result=result,
            history_limit=self.history_limit,
            source="system",
        )

    def _prefix_result_message(
        self,
        result: dict[str, Any],
        prefix: str,
        extra_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return the original result with a prefixed message and merged data."""
        updated_result = dict(result)
        updated_result["message"] = f"{prefix} {str(result.get('message', '')).strip()}".strip()

        merged_data: dict[str, Any] = {}
        if isinstance(result.get("data"), dict):
            merged_data.update(result["data"])
        if extra_data:
            merged_data.update(extra_data)
        updated_result["data"] = merged_data or None
        return updated_result

    def _describe_pending_action(self, intent: dict[str, str]) -> str:
        """Return a short label for the currently pending action."""
        intent_name = intent.get("intent", "command")
        if intent_name == "shutdown_computer":
            return "shutdown"
        if intent_name == "restart_computer":
            return "restart"
        return intent_name.replace("_", " ")

    def _get_history_limit(self) -> int:
        """Return a safe integer history limit from the loaded settings."""
        try:
            return max(0, int(self.settings.get("history_limit", DEFAULT_HISTORY_LIMIT)))
        except (TypeError, ValueError):
            return DEFAULT_HISTORY_LIMIT

    def _normalize_source(self, source: str) -> str:
        """Return a supported history source label."""
        normalized_source = source.strip().lower()
        if normalized_source in VALID_HISTORY_SOURCES:
            return normalized_source
        return "console"

    def _build_listen_settings(self) -> dict[str, Any]:
        """Return runtime listen settings, disabling wake-word checks for a follow-up turn."""
        listen_settings = dict(self.settings)
        if self.awaiting_followup_command:
            listen_settings["wake_word_enabled"] = False
        return listen_settings

    def _capture_console_fallback(self, message: str) -> dict[str, object] | None:
        """Prompt once for typed input when voice input is not working well."""
        if not bool(self.settings.get("console_fallback_enabled", True)):
            return None

        self.say(message, use_tts=False)
        console_settings = dict(self.settings)
        console_settings["speech_input_enabled"] = False
        console_settings["console_wake_word_optional"] = True
        return listen(settings=console_settings, logger=self.logger)


# TODO: Add wake-word mode and background listening in a future phase.


MakiBotAssistant = MakiAssistant
