"""File actions for safe folder creation and opening."""

import os
import subprocess
from pathlib import Path
from typing import Any

from app.services.app_registry import resolve_folder_path
from app.utils.helpers import build_result, normalize_text


def create_folder(folder_name: str, base_path: Path | None = None) -> dict[str, Any]:
    """Create a relative folder path inside the allowed base directory."""
    cleaned_name = normalize_text(folder_name)
    if not cleaned_name:
        return build_result(False, "Please provide a folder name.", {"status": "invalid_input"})

    requested_path = Path(cleaned_name)
    if requested_path.is_absolute():
        return build_result(False, "Please use a relative folder path.", {"status": "invalid_input"})

    safe_base_path = (base_path or Path.cwd()).resolve()
    target_path = (safe_base_path / requested_path).resolve()

    if safe_base_path != target_path and safe_base_path not in target_path.parents:
        return build_result(False, "Folder creation outside the workspace is not allowed.", {"status": "blocked"})

    try:
        target_path.mkdir(parents=True, exist_ok=True)
    except Exception as error:
        return build_result(False, f"Failed to create the folder: {error}", {"status": "error"})

    return build_result(True, f"Created folder at {target_path}.", {"status": "completed", "path": str(target_path)})


def open_folder(
    folder_name: str,
    registry: dict[str, Any] | None = None,
    base_path: Path | None = None,
) -> dict[str, Any]:
    """Open a registered folder alias or an existing workspace folder."""
    target_path = _resolve_folder_target(folder_name, registry=registry, base_path=base_path)
    if target_path is None:
        return build_result(False, f"I could not find a folder for '{folder_name}'.", {"status": "not_found"})

    if not target_path.exists() or not target_path.is_dir():
        return build_result(False, f"The folder '{target_path}' does not exist.", {"status": "not_found"})

    try:
        _open_directory(target_path)
    except Exception as error:
        return build_result(False, f"Failed to open the folder: {error}", {"status": "error"})

    return build_result(True, f"Opening folder {target_path}.", {"status": "completed", "path": str(target_path)})


def _resolve_folder_target(
    folder_name: str,
    registry: dict[str, Any] | None = None,
    base_path: Path | None = None,
) -> Path | None:
    """Resolve a folder name to a concrete safe path."""
    cleaned_name = normalize_text(folder_name)
    if not cleaned_name:
        return None

    registry_path = resolve_folder_path(cleaned_name, registry=registry)
    if registry_path is not None:
        return registry_path.expanduser()

    candidate_path = Path(cleaned_name).expanduser()
    if candidate_path.is_absolute():
        return candidate_path

    safe_base_path = (base_path or Path.cwd()).resolve()
    workspace_path = (safe_base_path / candidate_path).resolve()
    if safe_base_path == workspace_path or safe_base_path in workspace_path.parents:
        return workspace_path

    return None


def _open_directory(path: Path) -> None:
    """Open a directory using the current operating system."""
    if hasattr(os, "startfile"):
        os.startfile(str(path))
        return

    subprocess.Popen(["xdg-open", str(path)])


# TODO: Add safe file read and list commands when needed.
