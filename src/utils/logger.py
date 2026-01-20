"""Logging setup with basic rotation hook."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def init_logging(level: int = logging.INFO, log_path: Path | None = None) -> None:
    logger = logging.getLogger()
    if logger.handlers:
        return
    logger.setLevel(level)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)
    if log_path:
        handler = RotatingFileHandler(log_path, maxBytes=5_000_000, backupCount=3)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
