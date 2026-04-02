"""Structured profile extraction from local knowledge documents."""

from __future__ import annotations

import re
from pathlib import Path

from app.models.knowledge_documents import load_knowledge_text

_PREFERRED_TITLE_PATTERN = re.compile(r"^\s*preferred title\s*:\s*(.+?)\s*$", re.IGNORECASE)
_STARTUP_GREETING_PATTERN = re.compile(r"^\s*startup greeting\s*:\s*(.+?)\s*$", re.IGNORECASE)
_CALL_ME_PATTERN = re.compile(
    r"when referring to me,\s*call me\s+(.+?)(?:\s+unless\b|[.?!]|$)",
    re.IGNORECASE,
)


def load_master_profile(path: Path | None = None) -> dict[str, str]:
    """Return a small profile extracted from knowledge.txt when available."""
    content = load_knowledge_text(path=path)
    if not content:
        return {}

    profile: dict[str, str] = {}
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("["):
            continue

        preferred_title_match = _PREFERRED_TITLE_PATTERN.match(line)
        if preferred_title_match:
            profile["preferred_title"] = preferred_title_match.group(1).strip()
            continue

        startup_greeting_match = _STARTUP_GREETING_PATTERN.match(line)
        if startup_greeting_match:
            profile["startup_greeting"] = startup_greeting_match.group(1).strip()
            continue

        call_me_match = _CALL_ME_PATTERN.search(line)
        if call_me_match and "preferred_title" not in profile:
            profile["preferred_title"] = call_me_match.group(1).strip()

    return profile


def load_knowledge_profile(path: Path | None = None) -> dict[str, str]:
    """Compatibility alias for structured owner-profile loading."""
    return load_master_profile(path=path)
