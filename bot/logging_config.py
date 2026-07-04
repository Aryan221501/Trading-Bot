"""
Central logging configuration for the trading bot.

Every API request, response, and error is written to a rotating log file
(``logs/trading_bot.log``) as structured, single-line entries so they can
be grepped or parsed easily. A concise version of the same information is
also mirrored to the console so the user gets immediate feedback.

Log levels used throughout the project:
    DEBUG    - raw request/response payloads
    INFO     - high level lifecycle events (order submitted, order filled)
    WARNING  - recoverable issues (retrying a request, partial fill)
    ERROR    - failed API calls, validation failures, network errors
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
LOG_FILE = os.path.join(LOG_DIR, "trading_bot.log")

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure and return the root application logger.

    Parameters
    ----------
    verbose:
        When True, DEBUG-level messages (raw payloads) are also sent to the
        console. The log FILE always captures DEBUG and above regardless of
        this flag, so a full audit trail is always available on disk.
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger("trading_bot")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # Avoid duplicate handlers if setup_logging() is called more than once
    # (e.g. in tests).
    if logger.handlers:
        return logger

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # Rotating file handler: keeps the log directory bounded in size while
    # preserving history across runs (5 x 1MB backups).
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def get_logger() -> logging.Logger:
    """Return the already-configured application logger (or configure it
    with defaults if it hasn't been set up yet)."""
    logger = logging.getLogger("trading_bot")
    if not logger.handlers:
        return setup_logging()
    return logger
