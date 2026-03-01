import logging
import sys
from config import settings


def get_logger(name: str = "pattern_observer") -> logging.Logger:
    """Create a consistently formatted logger for the Pattern Observer service."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)
    return logger


# Module-level logger
logger = get_logger("pattern_observer")
