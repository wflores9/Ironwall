"""ironwall.core.logging — structured logger factory."""

import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """Return a logger with a consistent format across all ironwall modules."""
    logger = logging.getLogger(f"ironwall.{name}")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
        logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger
