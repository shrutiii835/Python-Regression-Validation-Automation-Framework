"""Centralized logging.

Call setup_logging() once at program start. Every other module simply does:

    from regression_framework.logger import get_logger
    logger = get_logger(__name__)

The log file always records everything (DEBUG and up), while the console only
shows messages at `console_level` or above, so the terminal stays readable.
"""

import logging
from pathlib import Path

ROOT_LOGGER_NAME = "regression"
FILE_FORMAT = "%(asctime)s | %(levelname)-7s | %(threadName)-10s | %(name)s | %(message)s"
CONSOLE_FORMAT = "%(levelname)s: %(message)s"


def setup_logging(log_dir: str | Path = "logs", console_level: str = "WARNING") -> Path:
    """Send log messages to the console and to logs/regression.log. Returns the log file path."""
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "regression.log"

    logger = logging.getLogger(ROOT_LOGGER_NAME)
    logger.setLevel(logging.DEBUG)

    # Remove old handlers so calling setup_logging() twice doesn't duplicate output.
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level.upper())
    console_handler.setFormatter(logging.Formatter(CONSOLE_FORMAT))
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(FILE_FORMAT))
    logger.addHandler(file_handler)

    return log_file


def get_logger(name: str) -> logging.Logger:
    """Return a child logger, e.g. 'regression.regression_framework.runner'."""
    return logging.getLogger(f"{ROOT_LOGGER_NAME}.{name}")
