"""Report generation utilities."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def write_json(data: Any, path: Path) -> None:
    path.write_text(json.dumps(data, indent=2))


def write_csv(rows: Iterable[dict[str, Any]], path: Path) -> None:
    rows = list(rows)
    if not rows:
        path.write_text("")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
