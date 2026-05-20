"""YAML configuration loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path("resources/config.default.yaml")


def load_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or DEFAULT_CONFIG_PATH
    if not cfg_path.exists():
        return {}
    with cfg_path.open() as fh:
        return yaml.safe_load(fh) or {}
