"""Logging configuration for the toolkit."""

from __future__ import annotations

import logging
from functools import lru_cache


@lru_cache()
def get_logger(name: str = "stock_toolkit") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("[%(levelname)s] %(name)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


