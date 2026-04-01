"""Application startup module for the MakiBot Phase 2 backend."""

from app.assistant import MakiBotAssistant
from app.config import BOT_NAME
from app.services.database import initialize_database
from app.services.settings_service import load_settings
from app.utils.logger import configure_logging, get_logger


def main() -> int:
    """Create the assistant and start the main command loop."""
    configure_logging()
    logger = get_logger(__name__)
    initialize_database(logger=logger)
    settings = load_settings()
    bot_name = str(settings.get("bot_name", BOT_NAME))

    logger.info("Starting %s.", bot_name)

    try:
        assistant = MakiBotAssistant(settings=settings)
        assistant.run()
    except KeyboardInterrupt:
        logger.info("Shutdown requested by keyboard interrupt.")
    except Exception:
        logger.exception("Unexpected fatal error while running the assistant.")
        return 1

    logger.info("%s stopped.", bot_name)
    return 0


# TODO: Add startup validation for optional dependencies later.
