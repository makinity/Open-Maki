"""Thin routes for settings operations."""

from typing import Any

from app.controllers.settings_controller import (
    load_settings,
    save_settings,
    update_settings,
)


def load_settings_route() -> dict[str, Any]:
    """Route for loading settings."""
    return load_settings()


def save_settings_route(payload: dict[str, Any]) -> dict[str, Any]:
    """Route for saving a full settings payload."""
    return save_settings(payload)


def update_settings_route(payload: dict[str, Any]) -> dict[str, Any]:
    """Route for updating part of the settings payload."""
    return update_settings(payload)

