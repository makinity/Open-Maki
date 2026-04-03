"""Application and media actions for safely opening apps and capturing local media."""

from __future__ import annotations

import os
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import BASE_DIR, PUBLIC_UPLOADS_DIR
from app.services.app_registry import resolve_app_entry
from app.utils.helpers import build_result

try:
    import cv2
except Exception:  # pragma: no cover - optional dependency
    cv2 = None

try:
    import mss
    from mss import tools as mss_tools
except Exception:  # pragma: no cover - optional dependency
    mss = None
    mss_tools = None

try:
    from PIL import ImageGrab
except Exception:  # pragma: no cover - optional dependency
    ImageGrab = None

try:
    import pyautogui
except Exception:  # pragma: no cover - optional dependency
    pyautogui = None

_WINDOWS_PROTOCOL_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
_DEFAULT_CAMERA_DEVICE_INDEX = 0
_DEFAULT_CAMERA_WARMUP_FRAMES = 3
_MAX_CAMERA_WARMUP_FRAMES = 6
_CAMERA_OUTPUT_DIR = PUBLIC_UPLOADS_DIR / "camera"
_SCREENSHOT_OUTPUT_DIR = PUBLIC_UPLOADS_DIR / "screenshots"
_BUILTIN_CLOSE_PROCESS_NAMES: dict[str, list[str]] = {
    "camera": ["WindowsCamera.exe"],
    "camera app": ["WindowsCamera.exe"],
    "webcam": ["WindowsCamera.exe"],
    "chrome": ["chrome.exe"],
    "google chrome": ["chrome.exe"],
    "edge": ["msedge.exe"],
    "microsoft edge": ["msedge.exe"],
    "vscode": ["code.exe"],
    "visual studio code": ["code.exe"],
    "code": ["code.exe"],
    "notepad": ["notepad.exe"],
    "paint": ["mspaint.exe"],
    "powershell": ["powershell.exe", "pwsh.exe"],
    "command prompt": ["cmd.exe"],
    "cmd": ["cmd.exe"],
    "calculator": ["CalculatorApp.exe", "calc.exe"],
    "calc": ["CalculatorApp.exe", "calc.exe"],
}


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
            f"I could not find an app alias for '{cleaned_target}'. Add it to the app_aliases table.",
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


def close_app(target: str, app_registry: dict[str, Any] | None = None) -> dict[str, Any]:
    """Close an application by alias using a known or inferred process name."""
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
            f"I could not find an app alias for '{cleaned_target}'. Add it to the app_aliases table.",
            {"status": "not_found", "target": cleaned_target},
        )

    display_name = str(app_entry.get("name", cleaned_target))
    process_names = _resolve_process_names(cleaned_target, app_entry)
    if not process_names:
        return build_result(
            False,
            f"I found the alias for {display_name}, but I do not know how to close it yet.",
            {"status": "not_supported", "target": display_name},
        )

    terminated_processes: list[str] = []
    errors: list[str] = []
    for process_name in process_names:
        termination_result = _terminate_process_by_name(process_name)
        status = str(termination_result.get("status", "")).strip().lower()
        if status == "completed":
            terminated_processes.append(process_name)
            continue
        if status == "error":
            error_message = str(termination_result.get("message", "")).strip()
            if error_message:
                errors.append(error_message)

    if terminated_processes:
        return build_result(
            True,
            f"Closing {display_name}.",
            {
                "status": "completed",
                "target": display_name,
                "process_names": terminated_processes,
            },
        )

    if errors:
        return build_result(
            False,
            f"Failed to close {display_name}.",
            {
                "status": "error",
                "target": display_name,
                "errors": errors,
            },
        )

    return build_result(
        False,
        f"{display_name} does not appear to be running.",
        {
            "status": "not_running",
            "target": display_name,
            "process_names": process_names,
        },
    )


def take_picture(settings: dict[str, Any] | None = None) -> dict[str, Any]:
    """Capture one picture from the default camera and save it under public/uploads."""
    settings = settings or {}
    if cv2 is None:
        return build_result(
            False,
            "Taking a picture requires the optional opencv-python package. Install it, then try again.",
            {"status": "dependency_missing", "target": "camera"},
        )

    camera_index = _coerce_int(
        settings.get("camera_device_index"),
        default=_DEFAULT_CAMERA_DEVICE_INDEX,
    )
    warmup_frames = _coerce_int(
        settings.get("camera_warmup_frames"),
        default=_DEFAULT_CAMERA_WARMUP_FRAMES,
        minimum=1,
        maximum=_MAX_CAMERA_WARMUP_FRAMES,
    )

    output_dir = _resolve_output_dir(
        settings.get("camera_output_dir"),
        default=_CAMERA_OUTPUT_DIR,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / _build_photo_filename()

    capture = _open_video_capture(camera_index)
    if capture is None or not bool(capture.isOpened()):
        return build_result(
            False,
            "I could not access the camera on this computer.",
            {"status": "unavailable", "target": "camera"},
        )

    frame = None
    try:
        for _ in range(warmup_frames):
            success, captured_frame = capture.read()
            if success:
                frame = captured_frame
            time.sleep(0.05)
    finally:
        capture.release()

    if frame is None:
        return build_result(
            False,
            "I opened the camera, but I could not capture a photo.",
            {"status": "capture_failed", "target": "camera"},
        )

    if not bool(cv2.imwrite(str(output_path), frame)):
        return build_result(
            False,
            "I captured the image, but I could not save it to disk.",
            {"status": "save_failed", "target": "camera"},
        )

    relative_path = _format_display_path(output_path)
    return build_result(
        True,
        f"I took a picture and saved it to {relative_path}.",
        {
            "status": "completed",
            "target": "camera",
            "path": str(output_path),
        },
    )


def take_screenshot(settings: dict[str, Any] | None = None) -> dict[str, Any]:
    """Capture one full-screen screenshot and save it under public/uploads."""
    settings = settings or {}
    if not _can_capture_screenshot():
        return build_result(
            False,
            "Taking a screenshot requires mss, Pillow ImageGrab, or pyautogui. Install one of them, then try again.",
            {"status": "dependency_missing", "target": "screen"},
        )

    output_dir = _resolve_output_dir(
        settings.get("screenshot_output_dir"),
        default=_SCREENSHOT_OUTPUT_DIR,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / _build_screenshot_filename()

    try:
        _capture_screenshot_to_path(output_path)
    except Exception as error:
        return build_result(
            False,
            f"I could not capture a screenshot: {error}",
            {"status": "capture_failed", "target": "screen"},
        )

    relative_path = _format_display_path(output_path)
    return build_result(
        True,
        f"I took a screenshot and saved it to {relative_path}.",
        {
            "status": "completed",
            "target": "screen",
            "path": str(output_path),
        },
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

    if hasattr(os, "startfile") and (
        command_path.exists() or _looks_like_windows_protocol(cleaned_command)
    ):
        os.startfile(cleaned_command)
        return

    subprocess.Popen([cleaned_command])


def _resolve_process_names(target: str, app_entry: dict[str, Any]) -> list[str]:
    """Return known or inferred process names for one app alias entry."""
    resolved_process_names: list[str] = []
    normalized_keys = {
        _normalize_alias_value(target),
        _normalize_alias_value(str(app_entry.get("name", ""))),
    }

    for normalized_key in normalized_keys:
        for process_name in _BUILTIN_CLOSE_PROCESS_NAMES.get(normalized_key, []):
            if process_name not in resolved_process_names:
                resolved_process_names.append(process_name)

    for process_name in _infer_process_names_from_command(app_entry.get("command")):
        if process_name not in resolved_process_names:
            resolved_process_names.append(process_name)

    return resolved_process_names


def _infer_process_names_from_command(command: Any) -> list[str]:
    """Infer likely process names from an app command when possible."""
    command_value: Any
    if isinstance(command, (list, tuple)) and command:
        command_value = command[0]
    else:
        command_value = command

    if not isinstance(command_value, str) or not command_value.strip():
        return []

    cleaned_command = command_value.strip().strip('"')
    if not cleaned_command or _looks_like_windows_protocol(cleaned_command):
        return []

    executable_name = Path(cleaned_command).name or cleaned_command
    executable_name = executable_name.strip()
    if not executable_name:
        return []

    if Path(executable_name).suffix:
        return [executable_name]

    if os.name == "nt":
        return [f"{executable_name}.exe"]

    return [executable_name]


def _terminate_process_by_name(process_name: str) -> dict[str, str]:
    """Terminate one process by name and return a normalized status payload."""
    if os.name == "nt":
        return _terminate_windows_process(process_name)

    return _terminate_posix_process(process_name)


def _terminate_windows_process(process_name: str) -> dict[str, str]:
    """Terminate one Windows process by image name."""
    try:
        completed_process = subprocess.run(
            ["taskkill", "/IM", process_name, "/T", "/F"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
            check=False,
        )
    except Exception as error:
        return {"status": "error", "message": str(error)}

    combined_output = " ".join(
        part.strip()
        for part in [completed_process.stdout, completed_process.stderr]
        if isinstance(part, str) and part.strip()
    )
    normalized_output = combined_output.lower()

    if completed_process.returncode == 0:
        return {"status": "completed", "message": combined_output}

    if "not found" in normalized_output or "no running instance" in normalized_output:
        return {"status": "not_running", "message": combined_output}

    return {
        "status": "error",
        "message": combined_output or f"taskkill returned exit code {completed_process.returncode}.",
    }


def _terminate_posix_process(process_name: str) -> dict[str, str]:
    """Terminate one POSIX process by executable name."""
    process_stem = Path(process_name).stem or process_name
    try:
        completed_process = subprocess.run(
            ["pkill", "-x", process_stem],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
            check=False,
        )
    except Exception as error:
        return {"status": "error", "message": str(error)}

    combined_output = " ".join(
        part.strip()
        for part in [completed_process.stdout, completed_process.stderr]
        if isinstance(part, str) and part.strip()
    )

    if completed_process.returncode == 0:
        return {"status": "completed", "message": combined_output}

    if completed_process.returncode == 1:
        return {"status": "not_running", "message": combined_output}

    return {
        "status": "error",
        "message": combined_output or f"pkill returned exit code {completed_process.returncode}.",
    }


def _normalize_alias_value(value: str) -> str:
    """Normalize an alias-style string for internal lookups."""
    return " ".join(str(value).strip().lower().split())


def _looks_like_windows_protocol(value: str) -> bool:
    """Return True when a command string looks like a Windows shell protocol target."""
    if os.name != "nt":
        return False

    cleaned_value = value.strip()
    if not cleaned_value or cleaned_value.startswith("\\\\"):
        return False

    return bool(_WINDOWS_PROTOCOL_PATTERN.match(cleaned_value)) and not Path(cleaned_value).exists()


def _open_video_capture(camera_index: int) -> Any:
    """Open the configured camera using a Windows-friendly backend when available."""
    if cv2 is None:
        return None

    if os.name == "nt" and hasattr(cv2, "CAP_DSHOW"):
        return cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)

    return cv2.VideoCapture(camera_index)


def _select_screenshot_monitor(screenshotter: Any) -> Any:
    """Return the full desktop monitor definition for screenshot capture."""
    monitors = getattr(screenshotter, "monitors", None)
    if isinstance(monitors, list) and monitors:
        return monitors[0]

    raise RuntimeError("No display monitor is available for screenshot capture.")


def _can_capture_screenshot() -> bool:
    """Return True when at least one screenshot backend is available."""
    return (mss is not None and mss_tools is not None) or ImageGrab is not None or pyautogui is not None


def _capture_screenshot_to_path(output_path: Path) -> None:
    """Capture one screenshot using the best available backend."""
    if mss is not None and mss_tools is not None:
        with mss.mss() as screenshotter:
            monitor = _select_screenshot_monitor(screenshotter)
            screenshot = screenshotter.grab(monitor)
            mss_tools.to_png(screenshot.rgb, screenshot.size, output=str(output_path))
        return

    if ImageGrab is not None:
        screenshot_image = ImageGrab.grab()
        screenshot_image.save(str(output_path))
        return

    if pyautogui is not None:
        screenshot_image = pyautogui.screenshot()
        screenshot_image.save(str(output_path))
        return

    raise RuntimeError("No screenshot backend is available.")


def _resolve_output_dir(raw_path: Any, default: Path) -> Path:
    """Return an output directory from settings or a feature-specific default folder."""
    if isinstance(raw_path, str) and raw_path.strip():
        return Path(raw_path.strip())

    return default


def _build_photo_filename() -> str:
    """Return a timestamped filename for one captured photo."""
    return f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"


def _build_screenshot_filename() -> str:
    """Return a timestamped filename for one captured screenshot."""
    return f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"


def _format_display_path(path: Path) -> str:
    """Return a user-facing path relative to the project root when possible."""
    try:
        return str(path.relative_to(BASE_DIR))
    except ValueError:
        return str(path)


def _coerce_int(
    value: Any,
    default: int,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    """Return a bounded integer value using a safe fallback."""
    try:
        parsed_value = int(value)
    except (TypeError, ValueError):
        parsed_value = default

    if minimum is not None:
        parsed_value = max(minimum, parsed_value)
    if maximum is not None:
        parsed_value = min(maximum, parsed_value)
    return parsed_value


# TODO: Add support for optional command arguments and explicit close metadata in registry entries.

