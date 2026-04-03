"""System actions for time, date, help text, exit, and power commands."""

import os
import subprocess
from datetime import datetime
from typing import Any

from app.speech.speak import get_available_voices
from app.utils.helpers import build_result

COMMAND_HELP: dict[str, str] = {
    "open_app": "Open a known desktop application, for example 'open notepad'.",
    "close_app": "Close a known desktop application, for example 'close camera' or 'close chrome'.",
    "take_picture": "Capture one photo from the default camera and save it under public/uploads/camera.",
    "open_website": "Open a website alias or URL, for example 'go to youtube'.",
    "search_website": "Search any website that has a search URL template in MySQL, for example 'search github for makibot'.",
    "search_google": "Search Google, for example 'google python decorators'.",
    "search_youtube": "Search YouTube, for example 'youtube jazz piano'.",
    "tell_time": "Tell the current local time.",
    "tell_date": "Tell today's local date.",
    "list_voices": "List the text-to-speech voices currently available on this computer.",
    "create_folder": "Create a folder inside the project workspace.",
    "open_folder": "Open a known folder such as Downloads or a workspace folder.",
    "type_text": "Preview typed text, or type for real when enabled in settings.",
    "shutdown_computer": "Request a computer shutdown after confirmation.",
    "restart_computer": "Request a computer restart after confirmation.",
    "list_commands": "List the commands the assistant currently supports.",
    "help": "Show a short help summary.",
    "exit_bot": "Exit the assistant loop.",
}


def tell_current_time() -> dict[str, Any]:
    """Return the current local time as a friendly assistant response."""
    current_time = datetime.now().strftime("%I:%M %p").lstrip("0")
    return build_result(True, f"The current time is {current_time}.", {"status": "completed"})


def tell_current_date() -> dict[str, Any]:
    """Return the current local date as a friendly assistant response."""
    current_date = datetime.now().strftime("%A, %B %d, %Y")
    return build_result(True, f"Today's date is {current_date}.", {"status": "completed"})


def list_voices() -> dict[str, Any]:
    """Return the text-to-speech voices available on the current machine."""
    voices = get_available_voices()
    if not voices:
        return build_result(
            False,
            "I could not find any available text-to-speech voices on this computer.",
            {"status": "unavailable", "voices": []},
        )

    voice_names = [str(voice.get("name", "Unknown voice")) for voice in voices]
    return build_result(
        True,
        "Here are the voices I found: " + ", ".join(voice_names) + ".",
        {"status": "completed", "voices": voices},
    )


def list_commands() -> dict[str, Any]:
    """Return the list of currently supported commands."""
    commands = [{"intent": intent, "description": description} for intent, description in COMMAND_HELP.items()]
    return build_result(True, "Here are the commands I currently support.", {"status": "completed", "commands": commands})


def help_command() -> dict[str, Any]:
    """Return a short help summary with the supported command list."""
    result = list_commands()
    result["message"] = "I can open and close apps, open websites, search the web, manage folders, list available voices, tell the time and date, take pictures with the camera, and handle safe system requests."
    return result


def shutdown_computer(allow_system_commands: bool = False) -> dict[str, Any]:
    """Shut down the computer when system power commands are enabled."""
    if not allow_system_commands:
        return build_result(
            True,
            "Shutdown confirmed, but system power commands are disabled in settings.",
            {"status": "blocked", "action": "shutdown_computer", "executed": False},
        )

    return _run_power_command(
        ["shutdown", "/s", "/t", "0"] if os.name == "nt" else ["shutdown", "-h", "now"],
        "Shutting down the computer.",
        "shutdown_computer",
    )


def restart_computer(allow_system_commands: bool = False) -> dict[str, Any]:
    """Restart the computer when system power commands are enabled."""
    if not allow_system_commands:
        return build_result(
            True,
            "Restart confirmed, but system power commands are disabled in settings.",
            {"status": "blocked", "action": "restart_computer", "executed": False},
        )

    return _run_power_command(
        ["shutdown", "/r", "/t", "0"] if os.name == "nt" else ["shutdown", "-r", "now"],
        "Restarting the computer.",
        "restart_computer",
    )


def exit_bot() -> dict[str, Any]:
    """Return a friendly exit response for ending the assistant loop."""
    return build_result(True, "Goodbye.", {"status": "completed", "should_exit": True})


def _run_power_command(command: list[str], message: str, action: str) -> dict[str, Any]:
    """Execute a system power command with safe error handling."""
    try:
        subprocess.Popen(command)
    except Exception as error:
        return build_result(False, f"Failed to run {action}: {error}", {"status": "error", "executed": False})

    return build_result(True, message, {"status": "completed", "action": action, "executed": True})


# TODO: Add more safe system information commands in a later phase.
