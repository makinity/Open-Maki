"""PyWebView bridge methods for the first Maki desktop UI scaffold."""

from __future__ import annotations

from datetime import datetime
from queue import Empty, Queue
from threading import Event, Lock, Thread
from time import monotonic
from typing import Any

from app.config import BOT_NAME
from app.controllers.assistant_controller import AssistantController
from app.services.chat_response_service import build_startup_greeting
from app.speech.listen import listen
from app.speech.speak import speak
from app.utils.helpers import normalize_text


class _VoiceStandbySession:
    """Run one background listen cycle at a time for the desktop UI."""

    def __init__(
        self,
        process_once: Any,
        logger: Any | None = None,
        idle_delay_seconds: float = 0.35,
        paused_delay_seconds: float = 0.2,
    ) -> None:
        self._process_once = process_once
        self._logger = logger
        self._idle_delay_seconds = max(0.05, float(idle_delay_seconds))
        self._paused_delay_seconds = max(0.05, float(paused_delay_seconds))
        self._enabled = False
        self._enabled_lock = Lock()
        self._wake_event = Event()
        self._stop_event = Event()
        self._thread: Thread | None = None

    def start(self) -> None:
        """Start the background standby loop."""
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = Thread(
            target=self._run,
            name="maki-ui-voice-standby",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout_seconds: float = 1.0) -> None:
        """Stop the background standby loop."""
        self.disable()
        self._stop_event.set()
        self._wake_event.set()

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=max(0.1, float(timeout_seconds)))

    def enable(self) -> None:
        """Enable background voice standby."""
        with self._enabled_lock:
            self._enabled = True
        self._wake_event.set()

    def disable(self) -> None:
        """Pause background voice standby."""
        with self._enabled_lock:
            self._enabled = False
        self._wake_event.set()

    def is_enabled(self) -> bool:
        """Return the current background standby state."""
        with self._enabled_lock:
            return self._enabled

    def _run(self) -> None:
        """Process standby turns until the session is stopped."""
        while not self._stop_event.is_set():
            if not self.is_enabled():
                self._wake_event.wait(self._paused_delay_seconds)
                self._wake_event.clear()
                continue

            try:
                self._process_once()
            except Exception as error:  # pragma: no cover - defensive fallback
                if self._logger is not None:
                    self._logger.warning("Voice standby loop failed: %s", error)
                self.disable()

            if self._stop_event.wait(self._idle_delay_seconds):
                break


class _SpeechPlaybackSession:
    """Run assistant speech output on one background worker thread."""

    def __init__(
        self,
        process_once: Any,
        logger: Any | None = None,
    ) -> None:
        self._process_once = process_once
        self._logger = logger
        self._queue: Queue[str] = Queue()
        self._stop_event = Event()
        self._thread: Thread | None = None

    def start(self) -> None:
        """Start the background speech worker."""
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = Thread(
            target=self._run,
            name="maki-ui-speech-playback",
            daemon=True,
        )
        self._thread.start()

    def enqueue(self, response: str) -> None:
        """Queue one assistant response for speech playback."""
        cleaned_response = normalize_text(str(response))
        if cleaned_response:
            self._queue.put(cleaned_response)

    def stop(self, timeout_seconds: float = 1.0) -> None:
        """Stop the background speech worker."""
        self._stop_event.set()
        self._queue.put("")

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=max(0.1, float(timeout_seconds)))

    def _run(self) -> None:
        """Speak queued responses until the worker is stopped."""
        while not self._stop_event.is_set():
            try:
                response = self._queue.get(timeout=0.2)
            except Empty:
                continue

            if self._stop_event.is_set():
                break

            if not response:
                continue

            try:
                self._process_once(response)
            except Exception as error:  # pragma: no cover - defensive fallback
                if self._logger is not None:
                    self._logger.warning("Speech playback loop failed: %s", error)


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
        self._interaction_lock = Lock()
        self._mic_active = False
        self._auto_listen_enabled = False
        self._voice_session = _VoiceStandbySession(
            process_once=self._process_voice_standby_turn,
            logger=getattr(assistant_controller, "logger", None),
        )
        self._speech_session = _SpeechPlaybackSession(
            process_once=self._play_speech_response,
            logger=getattr(assistant_controller, "logger", None),
        )
        self._speech_session.start()
        self._startup_announced = False
        self._speaking_active = False
        self._speaking_until = 0.0
        self._status = self._build_status(
            "ready",
            f"{self.bot_name} desktop UI is ready.",
        )
        self._recent_activity = [
            self._build_activity(
                "system",
                "Desktop UI ready. Voice standby will start automatically, or you can type a command.",
            )
        ]

    def get_bootstrap_data(self) -> dict[str, Any]:
        """Return the initial UI payload used during frontend startup."""
        startup_message = ""
        should_speak_startup = False
        with self._lock:
            if not self._startup_announced:
                self._startup_announced = True
                startup_message = self._build_startup_message()
                if startup_message:
                    self._status = self._build_status("ready", startup_message)
                    self._recent_activity.append(
                        self._build_activity("assistant", startup_message)
                    )
                    should_speak_startup = True
            snapshot = self._build_ui_snapshot_locked()

        if should_speak_startup:
            self._speak_response(startup_message)
            return self.get_ui_state()

        return snapshot

    def get_ui_state(self) -> dict[str, Any]:
        """Return the latest UI state for polling updates."""
        with self._lock:
            return self._build_ui_snapshot_locked()

    def send_command(self, command: str) -> dict[str, Any]:
        """Accept one typed command and return a real assistant backend response."""
        normalized_command = normalize_text(str(command))

        with self._interaction_lock:
            if not normalized_command:
                response = "Type a command before sending it to Maki."
                with self._lock:
                    self._status = self._build_status("error", response)
                    self._recent_activity.append(self._build_activity("system", response))
                return {
                    "ok": False,
                    "command": "",
                    "response": response,
                    **self.get_ui_state(),
                    "meta": {
                        "result_status": "validation_error",
                        "requires_confirmation": False,
                        "should_exit": False,
                        "source": "ui",
                    },
                }

            with self._lock:
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
                with self._lock:
                    self._status = self._build_status("error", response)
                    self._recent_activity.append(
                        self._build_activity("system", f"{response} {error}")
                    )
                return {
                    "ok": False,
                    "command": normalized_command,
                    "response": response,
                    **self.get_ui_state(),
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
            with self._lock:
                self._recent_activity.append(self._build_activity("assistant", response))
                self._status = self._build_status(
                    self._get_status_state(result=result, meta=meta),
                    response,
                )
            self._speak_response(response)
            return {
                "ok": bool(result.get("success", False)),
                "command": normalized_command,
                "response": response,
                **self.get_ui_state(),
                "meta": meta,
            }

    def start_voice_standby(self) -> dict[str, Any]:
        """Start the Python-side voice standby worker for the desktop UI."""
        with self._lock:
            self._auto_listen_enabled = True
            if not self._mic_active:
                self._status = self._build_status("ready", "Voice standby is active.")
            snapshot = self._build_ui_snapshot_locked()

        self._voice_session.start()
        self._voice_session.enable()
        return snapshot

    def toggle_mic(self) -> dict[str, Any]:
        """Pause or resume Python-side voice standby for the desktop UI."""
        if self._auto_listen_enabled or self._mic_active:
            with self._lock:
                self._auto_listen_enabled = False
                if self._mic_active:
                    self._status = self._build_status(
                        "listening",
                        "Voice standby will pause after this listen.",
                    )
                else:
                    self._status = self._build_status("ready", "Voice standby is paused.")
                snapshot = self._build_ui_snapshot_locked()
            self._voice_session.disable()
            return snapshot

        return self.start_voice_standby()

    def get_status(self) -> dict[str, str]:
        """Return the current UI status label and state."""
        with self._lock:
            return dict(self._status)

    def get_recent_activity(self) -> list[dict[str, str]]:
        """Return the in-memory desktop UI activity list."""
        with self._lock:
            return self._copy_activity()

    def close(self) -> None:
        """Stop any background UI worker threads."""
        self._voice_session.stop()
        self._speech_session.stop()

    def _get_assistant_controller(self) -> AssistantController:
        """Return a persistent assistant controller for UI-issued commands."""
        if self._assistant_controller is None:
            self._assistant_controller = AssistantController(settings=self.settings)
            self.bot_name = str(
                getattr(self._assistant_controller, "bot_name", self.bot_name) or self.bot_name
            )
        return self._assistant_controller

    def _build_ui_listen_settings(self) -> dict[str, Any]:
        """Return one-shot listen settings for the desktop UI standby worker."""
        assistant_controller = self._get_assistant_controller()
        listen_settings = dict(getattr(assistant_controller, "settings", self.settings))
        listen_settings["speech_input_enabled"] = True
        listen_settings["console_fallback_enabled"] = False
        listen_settings["wake_word_enabled"] = False
        listen_settings["console_wake_word_optional"] = False
        try:
            timeout_seconds = int(listen_settings.get("voice_timeout_seconds", 2))
        except (TypeError, ValueError):
            timeout_seconds = 2
        listen_settings["voice_timeout_seconds"] = max(1, min(timeout_seconds, 2))
        return listen_settings

    def _build_ui_snapshot_locked(self) -> dict[str, Any]:
        """Return the current frontend snapshot while the state lock is held."""
        return {
            "bot_name": self.bot_name,
            "status": dict(self._status),
            "activity": self._copy_activity(),
            "mic_active": self._mic_active,
            "auto_listen_enabled": self._auto_listen_enabled,
            "speaking_active": self._is_speaking_locked(),
        }

    def _build_startup_message(self) -> str:
        """Return the spoken startup greeting for the desktop UI bootstrap."""
        assistant_controller = self._get_assistant_controller()
        dynamic_greeting = build_startup_greeting(
            settings=getattr(assistant_controller, "settings", self.settings),
            knowledge_text=str(getattr(assistant_controller, "knowledge_text", "")),
            knowledge_profile=getattr(assistant_controller, "knowledge_profile", {}),
            logger=getattr(assistant_controller, "logger", None),
        )
        if dynamic_greeting:
            return dynamic_greeting

        build_ready_message = getattr(assistant_controller, "_build_ready_message", None)
        if callable(build_ready_message):
            startup_message = normalize_text(str(build_ready_message()))
            if startup_message:
                return startup_message

        return f"Good day, sir. {self.bot_name} desktop UI is ready."
    def _copy_activity(self) -> list[dict[str, str]]:
        """Return a shallow copy of the current activity list."""
        return [dict(item) for item in self._recent_activity]

    def _process_voice_standby_turn(self) -> None:
        """Capture and process one background voice-standby turn."""
        if not self._interaction_lock.acquire(blocking=False):
            return

        try:
            with self._lock:
                if not self._auto_listen_enabled or self._speaking_active:
                    return

                self._mic_active = True
                self._status = self._build_status("listening", "Listening for your command.")

            try:
                payload = listen(
                    settings=self._build_ui_listen_settings(),
                    logger=getattr(self._get_assistant_controller(), "logger", None),
                )
            except Exception as error:
                self._voice_session.disable()
                with self._lock:
                    self._mic_active = False
                    self._auto_listen_enabled = False
                    response = "Voice standby is unavailable right now."
                    self._status = self._build_status("error", response)
                    self._recent_activity.append(
                        self._build_activity("system", f"{response} {error}")
                    )
                return

            with self._lock:
                self._mic_active = False

            result_payload = self._handle_listen_payload(
                payload,
                silent_empty_results=True,
            )
            result_meta = result_payload.get("meta", {})
            result_status = str(result_meta.get("result_status", "")).strip().lower()
            if bool(result_meta.get("should_exit", False)) or result_status in {
                "error",
                "voice_request_error",
                "voice_unavailable",
            }:
                self._voice_session.disable()
                with self._lock:
                    self._auto_listen_enabled = False
        finally:
            self._interaction_lock.release()

    def _speak_response(self, response: str) -> None:
        """Queue one UI assistant response for background speech playback."""
        if not response:
            return

        with self._lock:
            self._speaking_active = True
            self._speaking_until = 0.0

        self._speech_session.start()
        self._speech_session.enqueue(response)

    def _play_speech_response(self, response: str) -> None:
        """Send one UI assistant response through the existing speech output path."""
        if not response:
            return

        try:
            assistant_controller = self._assistant_controller
            if assistant_controller is not None and hasattr(assistant_controller, "say"):
                assistant_controller.say(response)
                return

            speak(response, settings=self.settings)
        finally:
            with self._lock:
                self._speaking_active = False
                self._speaking_until = monotonic() + 0.55

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
            with self._lock:
                self._recent_activity.append(self._build_activity("user", recognized_text))
            try:
                result = self._get_assistant_controller().handle_text(
                    recognized_text,
                    source=source,
                )
            except Exception as error:
                response = "Something went wrong while handling that voice command."
                with self._lock:
                    self._status = self._build_status("error", response)
                    self._recent_activity.append(
                        self._build_activity("system", f"{response} {error}")
                    )
                return {
                    "ok": False,
                    "command": recognized_text,
                    "response": response,
                    **self.get_ui_state(),
                    "meta": self._build_listen_meta("error", source),
                }

            result_data = result.get("data") if isinstance(result.get("data"), dict) else {}
            response = normalize_text(str(result.get("message", "")))
            if not response:
                response = f"{self.bot_name} processed the voice command."

            meta = self._build_result_meta(result, result_data, source=source)
            with self._lock:
                self._recent_activity.append(self._build_activity("assistant", response))
                self._status = self._build_status(
                    self._get_status_state(result=result, meta=meta),
                    response,
                )
            self._speak_response(response)
            return {
                "ok": bool(result.get("success", False)),
                "command": recognized_text,
                "response": response,
                **self.get_ui_state(),
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
            with self._lock:
                self._status = self._build_status("ready", "Voice standby is active.")
            return {
                "ok": False,
                "command": "",
                "response": response,
                **self.get_ui_state(),
                "meta": self._build_listen_meta(status, source),
            }

        with self._lock:
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
            **self.get_ui_state(),
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

    def _is_speaking_locked(self) -> bool:
        """Return True while TTS is active or still within the UI grace window."""
        return self._speaking_active or monotonic() < self._speaking_until
