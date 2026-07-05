"""YAML configuration loader."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

# Find the project root relative to this file (src/duplicate_image_detector/config)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "default.yaml"


def load_config(path: Path | None = None) -> dict[str, Any]:
    env_path = os.environ.get("DUPDET_CONFIG_PATH")
    if env_path:
        cfg_path = Path(env_path)
    else:
        cfg_path = path or DEFAULT_CONFIG_PATH

    if not cfg_path.exists():
        return {}
    with cfg_path.open() as fh:
        return yaml.safe_load(fh) or {}
