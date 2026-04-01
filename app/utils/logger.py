"""Logging helpers for consistent console output across the application."""

import logging

_LOGGING_READY = False


def configure_logging(level: int = logging.INFO) -> None:
    """Configure application logging once for the current Python process."""
    global _LOGGING_READY

    if _LOGGING_READY:
        logging.getLogger().setLevel(level)
        return

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    _LOGGING_READY = True


def get_logger(name: str = "Maki") -> logging.Logger:
    """Return a logger after ensuring the shared logging setup exists."""
    configure_logging()
    return logging.getLogger(name)


# TODO: Add file logging and user-configurable log levels later.
