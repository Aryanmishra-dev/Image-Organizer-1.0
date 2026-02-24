"""Tests for core.cleaner – safe deletion, backup, and undo."""
from __future__ import annotations

from pathlib import Path

from core.cleaner import Cleaner, DeletionRecord


def test_dry_run_returns_targets(tmp_path: Path) -> None:
    f1 = tmp_path / "a.txt"
    f2 = tmp_path / "b.txt"
    f1.write_text("a")
    f2.write_text("b")

    cleaner = Cleaner(backup_dir=tmp_path / "backup")
    result = cleaner.dry_run([f1, f2])
    assert len(result) == 2
    assert f1 in result


def test_delete_with_backup_moves_files(tmp_path: Path) -> None:
    target = tmp_path / "data.txt"
    target.write_text("important data")
    backup_dir = tmp_path / "backup"

    cleaner = Cleaner(backup_dir=backup_dir)
    records = cleaner.delete_with_backup([target])

    assert not target.exists(), "Original should be gone"
    assert len(records) == 1
    assert records[0].backup.exists()
    assert records[0].backup.read_text() == "important data"


def test_delete_skips_missing_files(tmp_path: Path) -> None:
    missing = tmp_path / "nonexistent.txt"
    cleaner = Cleaner(backup_dir=tmp_path / "backup")
    records = cleaner.delete_with_backup([missing])
    assert len(records) == 0


def test_undo_latest_restores_files(tmp_path: Path) -> None:
    target = tmp_path / "restore_me.txt"
    target.write_text("restore data")
    backup_dir = tmp_path / "backup"

    cleaner = Cleaner(backup_dir=backup_dir)
    cleaner.delete_with_backup([target])
    assert not target.exists()

    cleaner.undo_latest()
    assert target.exists()
    assert target.read_text() == "restore data"


def test_unique_backup_path_avoids_collisions(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backup"
    cleaner = Cleaner(backup_dir=backup_dir)

    f1 = tmp_path / "file.txt"
    f1.write_text("first")
    cleaner.delete_with_backup([f1])

    # Re-create and delete again → backup name must differ
    f1.write_text("second")
    records = cleaner.delete_with_backup([f1])
    assert len(records) == 1
    assert records[0].backup.exists()
    assert records[0].backup.read_text() == "second"
