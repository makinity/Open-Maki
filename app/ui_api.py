"""PyWebView bridge methods for the first Maki desktop UI scaffold."""

from __future__ import annotations

from datetime import datetime
from threading import Lock
from typing import Any

from app.config import BOT_NAME
from app.controllers.assistant_controller import AssistantController
from app.speech.listen import listen
from app.speech.speak import speak
from app.utils.helpers import normalize_text


class MakiUIApi:
    """Expose a small, stable bridge for the desktop UI scaffold."""

    def __init__(
        self,
        settings: dict[str, Any] | None = None,
        assistant_controller: AssistantController | None = None,
    ) -> None:
        """Create the UI bridge with in-memory session state only."""
        inherited_settings = getattr(assistant_controller, "settings", None)
        self.settings = dict(settings or inherited_settings or {})
        inherited_bot_name = str(getattr(assistant_controller, "bot_name", "")).strip()
        self.bot_name = str(self.settings.get("bot_name", inherited_bot_name or BOT_NAME))
        self._assistant_controller = assistant_controller
        self._lock = Lock()
        self._mic_active = False
        self._auto_listen_enabled = True
        self._status = self._build_status(
            "ready",
            f"{self.bot_name} desktop UI is ready.",
        )
        self._recent_activity = [
            self._build_activity(
                "system",
                "Desktop UI ready. Voice standby starts automatically, or you can type a command.",
            )
        ]

    def get_bootstrap_data(self) -> dict[str, Any]:
        """Return the initial UI payload used during frontend startup."""
        with self._lock:
            return {
                "bot_name": self.bot_name,
                "status": dict(self._status),
                "activity": self._copy_activity(),
                "mic_active": self._mic_active,
                "auto_listen_enabled": self._auto_listen_enabled,
            }

    def send_command(self, command: str) -> dict[str, Any]:
        """Accept one typed command and return a real assistant backend response."""
        normalized_command = normalize_text(str(command))

        with self._lock:
            if not normalized_command:
                response = "Type a command before sending it to Maki."
                self._status = self._build_status("error", response)
                self._recent_activity.append(self._build_activity("system", response))
                return {
                    "ok": False,
                    "command": "",
                    "response": response,
                    "status": dict(self._status),
                    "activity": self._copy_activity(),
                    "meta": {
                        "result_status": "validation_error",
                        "requires_confirmation": False,
                        "should_exit": False,
                        "source": "ui",
                    },
                }

            self._status = self._build_status(
                "processing",
                f"{self.bot_name} is processing your command.",
            )
            self._recent_activity.append(self._build_activity("user", normalized_command))

            try:
                result = self._get_assistant_controller().handle_text(
                    normalized_command,
                    source="ui",
                )
            except Exception as error:
                response = "Something went wrong while sending that command to Maki."
                self._status = self._build_status("error", response)
                self._recent_activity.append(
                    self._build_activity("system", f"{response} {error}")
                )
                return {
                    "ok": False,
                    "command": normalized_command,
                    "response": response,
                    "status": dict(self._status),
                    "activity": self._copy_activity(),
                    "meta": {
                        "result_status": "error",
                        "requires_confirmation": False,
                        "should_exit": False,
                        "source": "ui",
                    },
                }

            result_data = result.get("data") if isinstance(result.get("data"), dict) else {}
            response = normalize_text(str(result.get("message", "")))
            if not response:
                response = f"{self.bot_name} processed the command."

            meta = self._build_result_meta(result, result_data)
            self._recent_activity.append(self._build_activity("assistant", response))
            self._speak_response(response)
            self._status = self._build_status(
                self._get_status_state(result=result, meta=meta),
                response,
            )
            return {
                "ok": bool(result.get("success", False)),
                "command": normalized_command,
                "response": response,
                "status": dict(self._status),
                "activity": self._copy_activity(),
                "meta": meta,
            }

    def toggle_mic(self, silent_empty_results: bool = False) -> dict[str, Any]:
        """Capture one voice command from the desktop UI and process it."""
        with self._lock:
            self._mic_active = True
            self._status = self._build_status("listening", "Listening for your command.")

            try:
                payload = listen(
                    settings=self._build_ui_listen_settings(),
                    logger=getattr(self._get_assistant_controller(), "logger", None),
                )
            except Exception as error:
                self._mic_active = False
                response = "Voice input is unavailable right now."
                self._status = self._build_status("error", response)
                self._recent_activity.append(
                    self._build_activity("system", f"{response} {error}")
                )
                return {
                    "ok": False,
                    "command": "",
                    "response": response,
                    "mic_active": self._mic_active,
                    "status": dict(self._status),
                    "activity": self._copy_activity(),
                    "meta": self._build_listen_meta("voice_unavailable", "voice"),
                }

            self._mic_active = False
            return self._handle_listen_payload(
                payload,
                silent_empty_results=bool(silent_empty_results),
            )

    def get_status(self) -> dict[str, str]:
        """Return the current UI status label and state."""
        with self._lock:
            return dict(self._status)

    def get_recent_activity(self) -> list[dict[str, str]]:
        """Return the in-memory desktop UI activity list."""
        with self._lock:
            return self._copy_activity()

    def _get_assistant_controller(self) -> AssistantController:
        """Return a persistent assistant controller for UI-issued commands."""
        if self._assistant_controller is None:
            self._assistant_controller = AssistantController(settings=self.settings)
            self.bot_name = str(
                getattr(self._assistant_controller, "bot_name", self.bot_name) or self.bot_name
            )
        return self._assistant_controller

    def _build_ui_listen_settings(self) -> dict[str, Any]:
        """Return one-shot listen settings for the desktop UI mic button."""
        assistant_controller = self._get_assistant_controller()
        listen_settings = dict(getattr(assistant_controller, "settings", self.settings))
        listen_settings["speech_input_enabled"] = True
        listen_settings["console_fallback_enabled"] = False
        listen_settings["wake_word_enabled"] = False
        listen_settings["console_wake_word_optional"] = False
        return listen_settings

    def _copy_activity(self) -> list[dict[str, str]]:
        """Return a shallow copy of the current activity list."""
        return [dict(item) for item in self._recent_activity]

    def _speak_response(self, response: str) -> None:
        """Send one UI assistant response through the existing speech output path."""
        if not response:
            return

        assistant_controller = self._assistant_controller
        if assistant_controller is not None and hasattr(assistant_controller, "say"):
            assistant_controller.say(response)
            return

        speak(response, settings=self.settings)

    def _handle_listen_payload(
        self,
        payload: dict[str, Any],
        silent_empty_results: bool = False,
    ) -> dict[str, Any]:
        """Map one microphone payload into a UI response payload."""
        recognized_text = normalize_text(str(payload.get("text", "")))
        source = self._normalize_activity_source(str(payload.get("source", "voice")))
        status = normalize_text(str(payload.get("status", "empty"))).lower() or "empty"

        if recognized_text:
            self._recent_activity.append(self._build_activity("user", recognized_text))
            try:
                result = self._get_assistant_controller().handle_text(
                    recognized_text,
                    source=source,
                )
            except Exception as error:
                response = "Something went wrong while handling that voice command."
                self._status = self._build_status("error", response)
                self._recent_activity.append(
                    self._build_activity("system", f"{response} {error}")
                )
                return {
                    "ok": False,
                    "command": recognized_text,
                    "response": response,
                    "mic_active": self._mic_active,
                    "status": dict(self._status),
                    "activity": self._copy_activity(),
                    "meta": self._build_listen_meta("error", source),
                }

            result_data = result.get("data") if isinstance(result.get("data"), dict) else {}
            response = normalize_text(str(result.get("message", "")))
            if not response:
                response = f"{self.bot_name} processed the voice command."

            meta = self._build_result_meta(result, result_data, source=source)
            self._recent_activity.append(self._build_activity("assistant", response))
            self._speak_response(response)
            self._status = self._build_status(
                self._get_status_state(result=result, meta=meta),
                response,
            )
            return {
                "ok": bool(result.get("success", False)),
                "command": recognized_text,
                "response": response,
                "mic_active": self._mic_active,
                "status": dict(self._status),
                "activity": self._copy_activity(),
                "meta": meta,
            }

        response = self._build_listen_message(status)
        if silent_empty_results and status in {
            "empty",
            "missing_wake_word",
            "voice_timeout",
            "voice_unrecognized",
            "wake_word_only",
        }:
            self._status = self._build_status("ready", "Voice standby is active.")
            return {
                "ok": False,
                "command": "",
                "response": response,
                "mic_active": self._mic_active,
                "status": dict(self._status),
                "activity": self._copy_activity(),
                "meta": self._build_listen_meta(status, source),
            }

        self._status = self._build_status(
            "error" if status in {"voice_request_error", "voice_unavailable"} else "ready",
            response,
        )
        self._recent_activity.append(self._build_activity("system", response))
        self._speak_response(response)
        return {
            "ok": False,
            "command": "",
            "response": response,
            "mic_active": self._mic_active,
            "status": dict(self._status),
            "activity": self._copy_activity(),
            "meta": self._build_listen_meta(status, source),
        }

    def _build_result_meta(
        self,
        result: dict[str, Any],
        result_data: dict[str, Any],
        source: str = "ui",
    ) -> dict[str, Any]:
        """Return stable metadata describing the assistant result for the UI."""
        result_status = str(result_data.get("status", "")).strip()
        if not result_status:
            result_status = "completed" if bool(result.get("success", False)) else "failed"

        return {
            "result_status": result_status,
            "requires_confirmation": bool(result_data.get("requires_confirmation", False)),
            "should_exit": bool(result_data.get("should_exit", False)),
            "source": source,
        }

    def _get_status_state(self, result: dict[str, Any], meta: dict[str, Any]) -> str:
        """Map assistant results into the UI status-state vocabulary."""
        if bool(meta.get("should_exit", False)):
            return "idle"

        result_status = str(meta.get("result_status", "")).strip().lower()
        if result_status in {"error", "failed"}:
            return "error"

        if not bool(result.get("success", False)) and result_status not in {"unknown", "idle"}:
            return "error"

        return "ready"

    def _build_status(self, state: str, label: str) -> dict[str, str]:
        """Create a normalized status payload for the frontend."""
        return {
            "label": normalize_text(label),
            "state": state,
        }

    def _build_listen_meta(self, result_status: str, source: str) -> dict[str, Any]:
        """Return metadata for one-shot mic capture results."""
        return {
            "result_status": result_status,
            "requires_confirmation": False,
            "should_exit": False,
            "source": source,
        }

    def _build_listen_message(self, status: str) -> str:
        """Return a user-facing message for a voice-input status value."""
        if status == "voice_timeout":
            return "I didn't hear anything."
        if status == "voice_unrecognized":
            return "I heard something, but I couldn't understand it."
        if status == "voice_request_error":
            return "Voice recognition could not reach the transcription service."
        if status == "voice_unavailable":
            return "Voice input is unavailable right now."
        if status == "missing_wake_word":
            return "Press the microphone button, then say the command directly."
        if status == "wake_word_only":
            return "Say the command directly after pressing the microphone button."
        return "I didn't receive a voice command."

    def _normalize_activity_source(self, source: str) -> str:
        """Return a supported source label for UI activity and history routing."""
        normalized_source = normalize_text(source).lower()
        if normalized_source in {"voice", "console", "system", "ui"}:
            return normalized_source
        return "voice"

    def _build_activity(self, item_type: str, text: str) -> dict[str, str]:
        """Create one UI activity item with a user-friendly timestamp."""
        return {
            "type": normalize_text(item_type).lower() or "system",
            "text": normalize_text(text),
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }
