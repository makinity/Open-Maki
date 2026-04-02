"""Thin route aggregator for future API wiring."""

from app.routes.commands import route_command
from app.routes.settings import (
    load_settings_route,
    save_settings_route,
    update_settings_route,
)

__all__ = [
    "load_settings_route",
    "save_settings_route",
    "update_settings_route",
    "route_command",
]
