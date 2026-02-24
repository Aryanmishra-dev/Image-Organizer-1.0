"""Shared fixtures for the test suite."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure src/ is on the path so imports like `from core.scanner import ...` work.
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


@pytest.fixture()
def sample_files(tmp_path: Path) -> dict[str, Path]:
    """Create a set of sample files for testing."""
    files = {}

    # Text files
    for i in range(5):
        f = tmp_path / f"file_{i}.txt"
        f.write_text(f"content_{i}" * (i + 1))
        files[f"txt_{i}"] = f

    # Duplicate pair
    dup1 = tmp_path / "dup_a.txt"
    dup2 = tmp_path / "dup_b.txt"
    content = "duplicate content for testing"
    dup1.write_text(content)
    dup2.write_text(content)
    files["dup_a"] = dup1
    files["dup_b"] = dup2

    # Empty file (should be skipped by scanner)
    empty = tmp_path / "empty.txt"
    empty.write_text("")
    files["empty"] = empty

    # Hidden file
    hidden = tmp_path / ".hidden"
    hidden.write_text("hidden")
    files["hidden"] = hidden

    return files


@pytest.fixture()
def nested_dirs(tmp_path: Path) -> Path:
    """Create a nested directory structure with files."""
    (tmp_path / "a" / "b").mkdir(parents=True)
    (tmp_path / "a" / "c").mkdir(parents=True)
    (tmp_path / "__pycache__").mkdir()

    (tmp_path / "root.txt").write_text("root")
    (tmp_path / "a" / "mid.txt").write_text("mid")
    (tmp_path / "a" / "b" / "deep.txt").write_text("deep")
    (tmp_path / "a" / "c" / "deep2.txt").write_text("deep2")
    (tmp_path / "__pycache__" / "cached.pyc").write_bytes(b"\x00")

    return tmp_path
