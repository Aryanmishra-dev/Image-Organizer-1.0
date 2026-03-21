"""Tests for utils.logger – logging initialisation."""

from __future__ import annotations

import logging
from pathlib import Path

from utils.logger import init_logging


def test_init_logging_creates_console_handler() -> None:
    # Use a unique named logger so we don't pollute the root logger across tests
    logger = logging.getLogger("test_init_logging")
    logger.handlers.clear()

    # init_logging uses the root logger; clear it first then test
    root = logging.getLogger()
    root.handlers.clear()

    init_logging(level=logging.DEBUG)
    assert len(root.handlers) >= 1
    assert any(isinstance(h, logging.StreamHandler) for h in root.handlers)

    # Clean up
    root.handlers.clear()


def test_init_logging_idempotent() -> None:
    root = logging.getLogger()
    root.handlers.clear()

    init_logging()
    count = len(root.handlers)
    init_logging()  # Second call should be a no-op
    assert len(root.handlers) == count

    root.handlers.clear()


def test_init_logging_with_file(tmp_path: Path) -> None:
    root = logging.getLogger()
    root.handlers.clear()

    log_file = tmp_path / "app.log"
    init_logging(log_path=log_file)

    assert len(root.handlers) >= 2  # StreamHandler + RotatingFileHandler
    root.handlers.clear()
