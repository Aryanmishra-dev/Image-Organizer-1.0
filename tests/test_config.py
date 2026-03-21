"""Tests for utils.config – YAML configuration loader."""

from __future__ import annotations

from pathlib import Path

from utils.config import load_config


def test_load_default_config() -> None:
    """Loading from the shipped config.default.yaml should return a non-empty dict."""
    # This works when run from the project root (pytest is configured with pythonpath=src)
    cfg = load_config(Path("resources/config.default.yaml"))
    assert isinstance(cfg, dict)
    assert "scan" in cfg
    assert "detection" in cfg
    assert "performance" in cfg
    assert "safety" in cfg


def test_load_missing_config_returns_empty() -> None:
    cfg = load_config(Path("/nonexistent/config.yaml"))
    assert cfg == {}


def test_load_custom_config(tmp_path: Path) -> None:
    custom = tmp_path / "custom.yaml"
    custom.write_text("feature:\n  enabled: true\n")
    cfg = load_config(custom)
    assert cfg["feature"]["enabled"] is True
