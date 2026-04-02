"""Desktop UI entry point for the first Maki PyWebView scaffold."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from app.config import BASE_DIR, BOT_NAME
from app.services.database import get_database_error, initialize_database
from app.services.settings_service import load_settings
from app.ui_api import MakiUIApi
from app.utils.logger import configure_logging, get_logger

UI_INDEX_FILE = BASE_DIR / "ui" / "index.html"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 820
MIN_WINDOW_WIDTH = 980
MIN_WINDOW_HEIGHT = 680


def _import_webview() -> Any:
    """Import pywebview lazily so the module can be tested without the dependency."""
    try:
        return import_module("webview")
    except ImportError as error:
        raise RuntimeError(
            "pywebview is not installed. Run 'pip install pywebview' or install from requirements.txt."
        ) from error


def _get_ui_index_uri() -> str:
    """Return the file URI used to load the local desktop UI."""
    if not UI_INDEX_FILE.exists():
        raise FileNotFoundError(f"UI entrypoint not found: {UI_INDEX_FILE}")

    return UI_INDEX_FILE.resolve().as_uri()


def main() -> int:
    """Initialize startup dependencies and launch the desktop UI window."""
    configure_logging()
    logger = get_logger(__name__)

    if not initialize_database(logger=logger):
        logger.error("Startup aborted: %s", get_database_error())
        return 1

    try:
        settings = load_settings()
        webview = _import_webview()
        ui_index_uri = _get_ui_index_uri()
    except (RuntimeError, FileNotFoundError) as error:
        logger.error("Startup aborted: %s", str(error))
        return 1
    except Exception:
        logger.exception("Unexpected fatal error while preparing the desktop UI.")
        return 1

    bot_name = str(settings.get("bot_name", BOT_NAME))
    logger.info("Starting %s desktop UI.", bot_name)

    try:
        webview.create_window(
            title=bot_name,
            url=ui_index_uri,
            js_api=MakiUIApi(settings=settings),
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            min_size=(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT),
            resizable=True,
            frameless=False,
        )
        webview.start(debug=False)
    except KeyboardInterrupt:
        logger.info("Desktop UI shutdown requested by keyboard interrupt.")
    except Exception:
        logger.exception("Unexpected fatal error while running the desktop UI.")
        return 1

    logger.info("%s desktop UI stopped.", bot_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
