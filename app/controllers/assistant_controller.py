"""Business logic for assistant command handling."""

from typing import Any

from app.brain.intent_parser import parse_intent
from app.brain.llm_intent_parser import parse_intent_with_llm
from app.config import BOT_NAME, DEFAULT_HISTORY_LIMIT
from app.controllers.command_controller import route_command
from app.controllers.history_controller import add_history_entry
from app.controllers.knowledge_controller import load_knowledge_profile, load_knowledge_text
from app.controllers.registry_controller import load_app_registry
from app.controllers.settings_controller import load_settings
from app.services.chat_response_service import build_chat_reply, build_kind_command_reply
from app.speech.speak import speak
from app.utils.helpers import build_result, normalize_text
from app.utils.logger import get_logger

VALID_HISTORY_SOURCES = {"voice", "console", "system"}


class AssistantController:
    """Handle assistant state, parsing, confirmations, and response shaping."""

    def __init__(self, settings: dict[str, Any] | None = None) -> None:
        """Create a new assistant controller with runtime settings and registry data."""
        self.logger = get_logger(self.__class__.__name__)
        self.settings = settings or load_settings()
        self.app_registry = load_app_registry()
        self.knowledge_profile = load_knowledge_profile()
        self.knowledge_text = load_knowledge_text()
        self.bot_name = str(self.settings.get("bot_name", BOT_NAME))
        self.history_limit = self._get_history_limit()
        self.pending_confirmation: dict[str, str] | None = None
        self.awaiting_followup_command = False
        self.consecutive_voice_misses = 0

    def handle_text(self, text: str, source: str = "console") -> dict[str, Any]:
        """Parse raw user text, handle confirmations, and route the command."""
        normalized_source = self._normalize_source(source)
        intent, parser_source = self._parse_intent_with_fallback(text)
        self.logger.info(
            "Command received from %s using %s parser: %s",
            normalized_source,
            parser_source,
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

        result = self._enhance_result_message(
            user_text=text,
            intent=intent,
            result=result,
        )

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
        if self.awaiting_followup_command or bool(self.settings.get("conversation_mode_enabled", False)):
            listen_settings["wake_word_enabled"] = False
        return listen_settings

    def _capture_console_fallback(self, message: str) -> dict[str, object] | None:
        """Prompt once for typed input when voice input is not working well."""
        if not bool(self.settings.get("console_fallback_enabled", True)):
            return None

        self.say(message, use_tts=self._should_use_voice_prompts())
        console_settings = dict(self.settings)
        console_settings["speech_input_enabled"] = False
        console_settings["console_wake_word_optional"] = True
        return self.listen(console_settings)

    def _get_primary_wake_phrase(self) -> str:
        """Return the first configured wake phrase for user-facing prompts."""
        wake_phrases = self.settings.get("wake_phrases")
        if isinstance(wake_phrases, list):
            for phrase in wake_phrases:
                cleaned_phrase = normalize_text(str(phrase))
                if cleaned_phrase:
                    return cleaned_phrase

        return "hey maki"

    def _build_ready_message(self) -> str:
        """Return the startup message, optionally customized by knowledge.txt."""
        if bool(self.settings.get("conversation_mode_enabled", False)):
            ready_message = "Ready. Talk to me naturally or type a command."
        elif bool(self.settings.get("wake_word_enabled", False)):
            ready_message = (
                f"Ready. Say '{self._get_primary_wake_phrase()}' to wake me, or type a command."
            )
        else:
            ready_message = "Ready. Say or type a command."

        startup_greeting = str(self.knowledge_profile.get("startup_greeting", "")).strip()
        if startup_greeting:
            return f"{startup_greeting} {ready_message}".strip()

        preferred_title = str(self.knowledge_profile.get("preferred_title", "")).strip()
        if preferred_title:
            return f"Hello, {preferred_title}. {ready_message}".strip()

        return ready_message

    def _should_use_voice_prompts(self) -> bool:
        """Return True when assistant prompts should follow normal speech output."""
        return True

    def _enhance_result_message(
        self,
        user_text: str,
        intent: dict[str, str],
        result: dict[str, Any],
    ) -> dict[str, Any]:
        """Return the result with an optional conversationally enhanced message."""
        if not bool(self.settings.get("conversation_mode_enabled", False)):
            return result

        intent_name = str(intent.get("intent", "unknown"))
        llm_message: str | None
        if intent_name == "unknown":
            llm_message = build_chat_reply(
                user_text=user_text,
                settings=self.settings,
                knowledge_text=self.knowledge_text,
                knowledge_profile=self.knowledge_profile,
                logger=self.logger,
            )
        else:
            llm_message = build_kind_command_reply(
                user_text=user_text,
                intent=intent,
                result=result,
                settings=self.settings,
                knowledge_text=self.knowledge_text,
                knowledge_profile=self.knowledge_profile,
                logger=self.logger,
            )

        if not llm_message:
            return result

        updated_result = dict(result)
        updated_result["message"] = llm_message
        return updated_result

    def _parse_intent_with_fallback(self, text: str) -> tuple[dict[str, str], str]:
        """Return the winning intent and which parser produced it."""
        rule_intent = parse_intent(text)
        if rule_intent.get("intent") != "unknown":
            return rule_intent, "rule"

        llm_intent = parse_intent_with_llm(
            text=text,
            settings=self.settings,
            app_registry=self.app_registry,
            logger=self.logger,
        )
        if isinstance(llm_intent, dict):
            return llm_intent, "llm"

        return rule_intent, "rule"

    def listen(self, settings: dict[str, Any]) -> dict[str, Any]:
        """Capture one input payload using the runtime-specific listen implementation."""
        raise NotImplementedError
