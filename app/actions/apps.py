"""Application actions for safely opening desktop apps."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from app.services.app_registry import resolve_app_entry
from app.utils.helpers import build_result


def open_app(target: str, app_registry: dict[str, Any] | None = None) -> dict[str, Any]:
    """Open an application from the current app registry."""
    cleaned_target = target.strip()
    if not cleaned_target:
        return build_result(
            False,
            "No application name was provided.",
            {"status": "invalid_input"},
        )

    app_entry = resolve_app_entry(cleaned_target, registry=app_registry)
    if app_entry is None:
        return build_result(
            False,
            f"I could not find an app alias for '{cleaned_target}'. Add it to apps.json.",
            {"status": "not_found", "target": cleaned_target},
        )

    display_name = str(app_entry.get("name", cleaned_target))
    command = app_entry.get("command")

    try:
        _launch_command(command)
    except FileNotFoundError:
        return build_result(
            False,
            f"I found the alias for {display_name}, but its command is not available on this computer.",
            {"status": "not_available", "target": display_name},
        )
    except Exception as exc:
        return build_result(
            False,
            f"Failed to open {display_name}: {exc}",
            {"status": "error", "target": display_name},
        )

    return build_result(
        True,
        f"Opening {display_name}.",
        {"status": "completed", "target": display_name},
    )


def _launch_command(command: Any) -> None:
    """Launch an application command using a safe subprocess strategy."""
    if isinstance(command, list) and command:
        subprocess.Popen(command)
        return

    if not isinstance(command, str) or not command.strip():
        raise FileNotFoundError("Application command is missing.")

    cleaned_command = command.strip()
    command_path = Path(cleaned_command)

    if command_path.exists() and hasattr(os, "startfile"):
        os.startfile(str(command_path))
        return

    subprocess.Popen([cleaned_command])


# TODO: Add support for optional command arguments in registry entries.
