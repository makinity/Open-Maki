"""Thin routes for command dispatch."""

from typing import Any

from app.controllers.command_controller import route_command as route_command_controller


def route_command(
    intent: dict[str, str],
    settings: dict[str, Any] | None = None,
    app_registry: dict[str, Any] | None = None,
    logger: Any = None,
    confirmed: bool = False,
) -> dict[str, Any]:
    """Route a parsed command intent through the controller layer."""
    return route_command_controller(
        intent,
        settings=settings,
        app_registry=app_registry,
        logger=logger,
        confirmed=confirmed,
    )

