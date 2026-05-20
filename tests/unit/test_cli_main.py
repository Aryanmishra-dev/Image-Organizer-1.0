"""Tests for CLI command helpers."""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import click
import pytest

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

commands = importlib.import_module("duplicate_image_detector.cli.main")
_targets_from_group = commands._targets_from_group
_validate_similarity = commands._validate_similarity


def test_validate_similarity_accepts_valid_values() -> None:
    assert _validate_similarity(click.Context(click.Command("x")), None, 0) == 0
    assert _validate_similarity(click.Context(click.Command("x")), None, 64) == 64


def test_validate_similarity_rejects_out_of_range() -> None:
    with pytest.raises(click.BadParameter):
        _validate_similarity(click.Context(click.Command("x")), None, -1)
    with pytest.raises(click.BadParameter):
        _validate_similarity(click.Context(click.Command("x")), None, 65)


def test_targets_from_group_respects_keep_strategy(tmp_path: Path) -> None:
    old = tmp_path / "old.jpg"
    new = tmp_path / "new.jpg"
    old.write_text("a")
    new.write_text("a")

    # Force deterministic mtime ordering.
    old_mtime = 1_000_000.0
    new_mtime = 2_000_000.0
    os.utime(old, (old_mtime, old_mtime))
    os.utime(new, (new_mtime, new_mtime))

    scan_data = {
        "exact_duplicates": [
            {
                "group_id": 7,
                "files": [
                    {"path": str(old), "size": old.stat().st_size, "mtime": old.stat().st_mtime},
                    {"path": str(new), "size": new.stat().st_size, "mtime": new.stat().st_mtime},
                ],
            }
        ],
        "similar_images": [],
    }

    targets = _targets_from_group(scan_data, group_id=7, keep="newest")
    assert targets == [old]


def test_targets_from_group_returns_empty_for_unknown_group() -> None:
    scan_data = {"exact_duplicates": [], "similar_images": []}
    assert _targets_from_group(scan_data, group_id=999, keep="oldest") == []
