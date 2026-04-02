"""Business logic for local knowledge/profile access."""

from pathlib import Path

from app.models.knowledge_documents import load_knowledge_text as load_document_text
from app.models.master_profile import load_knowledge_profile as load_profile


def load_knowledge_text(path: Path | None = None) -> str:
    """Load the raw local knowledge document."""
    return load_document_text(path=path)


def load_knowledge_profile(path: Path | None = None) -> dict[str, str]:
    """Load the structured owner profile extracted from knowledge documents."""
    return load_profile(path=path)

