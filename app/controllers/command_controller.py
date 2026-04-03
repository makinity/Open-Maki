"""Command routing business logic for assistant actions."""

from typing import Any, Callable

from app.actions.apps import close_app, open_app, take_picture, take_screenshot
from app.actions.files import create_folder, open_folder
from app.actions.system import (
    exit_bot,
    help_command,
    list_commands,
    list_voices,
    restart_computer,
    shutdown_computer,
    tell_current_date,
    tell_current_time,
)
from app.actions.typing_actions import type_text
from app.actions.web import open_website, search_google, search_website, search_youtube
from app.config import BASE_DIR, DANGEROUS_INTENTS
from app.utils.helpers import build_result


def route_command(
    intent: dict[str, str],
    settings: dict[str, Any] | None = None,
    app_registry: dict[str, Any] | None = None,
    logger: Any = None,
    confirmed: bool = False,
) -> dict[str, Any]:
    """Route a parsed intent to the correct action handler."""
    settings = settings or {}
    app_registry = app_registry or {}

    intent_name = str(intent.get("intent", "unknown"))
    target = str(intent.get("target", "")).strip()
    site = str(intent.get("site", "")).strip()

    if logger is not None:
        logger.debug("Routing intent '%s' with target '%s'.", intent_name, target)

    if intent_name in DANGEROUS_INTENTS and _requires_confirmation(settings, confirmed):
        return _build_confirmation_result(intent_name, target)

    try:
        return _dispatch_intent(intent_name, target, site, settings, app_registry)
    except Exception as error:
        if logger is not None:
            logger.exception("Command routing failed for intent '%s'.", intent_name)
        return build_result(
            False,
            f"Something went wrong while handling '{intent_name}'.",
            {"status": "error", "error": str(error)},
        )


def _dispatch_intent(
    intent_name: str,
    target: str,
    site: str,
    settings: dict[str, Any],
    app_registry: dict[str, Any],
) -> dict[str, Any]:
    """Dispatch the already validated intent to a concrete action."""
    handlers: dict[str, Callable[[], dict[str, Any]]] = {
        "open_app": lambda: open_app(target, app_registry),
        "close_app": lambda: close_app(target, app_registry),
        "take_picture": lambda: take_picture(settings=settings),
        "take_screenshot": lambda: take_screenshot(settings=settings),
        "open_website": lambda: open_website(target),
        "search_website": lambda: search_website(site, target),
        "search_google": lambda: search_google(target),
        "search_youtube": lambda: search_youtube(target),
        "tell_time": tell_current_time,
        "tell_date": tell_current_date,
        "list_voices": list_voices,
        "create_folder": lambda: create_folder(target, base_path=BASE_DIR),
        "open_folder": lambda: open_folder(target, registry=app_registry, base_path=BASE_DIR),
        "type_text": lambda: type_text(
            target,
            live_mode=bool(settings.get("typing_live_mode", False)),
        ),
        "shutdown_computer": lambda: shutdown_computer(
            allow_system_commands=bool(settings.get("allow_system_commands", False)),
        ),
        "restart_computer": lambda: restart_computer(
            allow_system_commands=bool(settings.get("allow_system_commands", False)),
        ),
        "list_commands": list_commands,
        "help": help_command,
        "exit_bot": exit_bot,
        "confirm_yes": lambda: build_result(False, "There is no pending action to confirm.", {"status": "idle"}),
        "confirm_no": lambda: build_result(False, "There is no pending action to cancel.", {"status": "idle"}),
        "unknown": lambda: build_result(False, "I did not understand that command.", {"status": "unknown"}),
    }

    handler = handlers.get(intent_name)
    if handler is None:
        return build_result(False, f"'{intent_name}' is not implemented yet.", {"status": "unknown"})

    return handler()


def _requires_confirmation(settings: dict[str, Any], confirmed: bool) -> bool:
    """Return True when the current command must be confirmed before execution."""
    return bool(settings.get("require_confirmation", True)) and not confirmed


def _build_confirmation_result(intent_name: str, target: str) -> dict[str, Any]:
    """Return the confirmation prompt for a dangerous action."""
    action_text = _describe_dangerous_action(intent_name, target)
    return build_result(
        True,
        f"Are you sure you want me to {action_text}? Say yes to confirm or no to cancel.",
        {
            "status": "pending_confirmation",
            "requires_confirmation": True,
            "intent": intent_name,
            "target": target,
        },
    )


def _describe_dangerous_action(intent_name: str, target: str) -> str:
    """Return a short natural-language description for a dangerous action."""
    if intent_name == "shutdown_computer":
        return "shut down the computer"

    if intent_name == "restart_computer":
        return "restart the computer"

    if target:
        return f"run '{intent_name}' on '{target}'"

    return intent_name.replace("_", " ")
