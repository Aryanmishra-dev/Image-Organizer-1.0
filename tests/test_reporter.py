"""Tests for utils.reporter – report generation utilities."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from utils.reporter import write_csv, write_json


def test_write_json(tmp_path: Path) -> None:
    out = tmp_path / "report.json"
    data = {"groups": 5, "files": ["a.txt", "b.txt"]}
    write_json(data, out)

    loaded = json.loads(out.read_text())
    assert loaded["groups"] == 5
    assert len(loaded["files"]) == 2


def test_write_csv(tmp_path: Path) -> None:
    out = tmp_path / "report.csv"
    rows = [
        {"name": "file1.txt", "size": 100},
        {"name": "file2.txt", "size": 200},
    ]
    write_csv(rows, out)

    with out.open() as fh:
        reader = csv.DictReader(fh)
        result = list(reader)
    assert len(result) == 2
    assert result[0]["name"] == "file1.txt"


def test_write_csv_empty(tmp_path: Path) -> None:
    out = tmp_path / "empty.csv"
    write_csv([], out)
    assert out.read_text() == ""
