"""YAML configuration loader."""
from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any, Dict

DEFAULT_CONFIG_PATH = Path("resources/config.default.yaml")


def load_config(path: Path | None = None) -> Dict[str, Any]:
    cfg_path = path or DEFAULT_CONFIG_PATH
    if not cfg_path.exists():
        return {}
    with cfg_path.open() as fh:
        return yaml.safe_load(fh) or {}
