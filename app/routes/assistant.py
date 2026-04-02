"""Thin route/runtime layer for the assistant loop."""

from app.controllers.assistant_controller import AssistantController
from app.speech.listen import listen
from app.utils.helpers import normalize_text

VOICE_MISS_LIMIT_FOR_CONSOLE = 1


class AssistantRoute(AssistantController):
    """Run the assistant loop using the controller for business logic."""

    def run(self) -> None:
        """Start the assistant command loop until an exit command is received."""
        self.say(self._build_ready_message())

        while True:
            payload = self.listen(self._build_listen_settings())
            text = normalize_text(str(payload.get("text", "")))
            source = self._normalize_source(str(payload.get("source", "none")))
            status = str(payload.get("status", "ok")).strip().lower()

            if status == "wake_word_only":
                self.consecutive_voice_misses = 0
                self.awaiting_followup_command = True
                self.say("I'm listening.", use_tts=self._should_use_voice_prompts())
                continue

            if status == "missing_wake_word":
                self.consecutive_voice_misses = 0
                self.say(
                    f"Please start with a wake phrase, like '{self._get_primary_wake_phrase()} open chrome'.",
                    use_tts=self._should_use_voice_prompts(),
                )
                continue

            if status in {"voice_timeout", "voice_unrecognized"}:
                if self.awaiting_followup_command:
                    self.awaiting_followup_command = False
                    self.consecutive_voice_misses = 0
                    self.say(
                        "I didn't catch the follow-up command.",
                        use_tts=self._should_use_voice_prompts(),
                    )
                    fallback_payload = self._capture_console_fallback(
                        "You can type the command instead."
                    )
                    if fallback_payload is None:
                        continue

                    text = normalize_text(str(fallback_payload.get("text", "")))
                    source = self._normalize_source(str(fallback_payload.get("source", "console")))
                    status = str(fallback_payload.get("status", "ok")).strip().lower()
                    if status == "wake_word_only":
                        self.consecutive_voice_misses = 0
                        self.awaiting_followup_command = True
                        self.say("I'm listening.", use_tts=self._should_use_voice_prompts())
                        continue
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
                    if status == "wake_word_only":
                        self.consecutive_voice_misses = 0
                        self.awaiting_followup_command = True
                        self.say("I'm listening.", use_tts=self._should_use_voice_prompts())
                        continue
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

    def listen(self, settings: dict[str, object]) -> dict[str, object]:
        """Capture one input payload for the assistant runtime."""
        return listen(settings=settings, logger=self.logger)


MakiAssistant = AssistantRoute
MakiBotAssistant = AssistantRoute

