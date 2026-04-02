"""Raw document access for local knowledge content."""

from pathlib import Path

from app.config import KNOWLEDGE_FILE


def load_knowledge_text(path: Path | None = None) -> str:
    """Return the full knowledge.txt content, or an empty string when missing."""
    knowledge_path = path or KNOWLEDGE_FILE
    try:
        return knowledge_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""
