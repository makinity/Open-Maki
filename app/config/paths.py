"""Filesystem path constants used by the application."""

from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
BASE_DIR = APP_DIR.parent
HOME_DIR = Path.home()

PUBLIC_DIR = BASE_DIR / "public"
PUBLIC_IMAGES_DIR = PUBLIC_DIR / "images"
PUBLIC_UPLOADS_DIR = PUBLIC_DIR / "uploads"

KNOWLEDGE_FILE = BASE_DIR / "knowledge.txt"
ENV_FILE = BASE_DIR / ".env"
