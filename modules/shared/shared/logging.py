"""Centralized logging configuration for wis2downloader modules."""
import logging
import os
import sys
import time
from typing import Optional


def setup_logging(name: Optional[str] = None, level: Optional[str] = None) -> logging.Logger:
    """
    Set up standardized logging with UTC timestamps.

    Args:
        name: Logger name (typically __name__). If None, configures root logger.
        level: Log level string. Defaults to LOG_LEVEL env var or DEBUG.

    Returns:
        Configured logger instance.
    """
    log_level = level or os.getenv("LOG_LEVEL", "DEBUG").upper()

    formatter = logging.Formatter(
        fmt='%(asctime)s.%(msecs)03dZ %(name)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S'
    )
    formatter.converter = time.gmtime

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    if name is None:
        root.handlers.clear()
        root.addHandler(handler)
        root.setLevel(log_level)
        return root

    if not root.handlers:
        root.addHandler(handler)

    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    return logger
