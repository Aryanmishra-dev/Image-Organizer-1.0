"""Integration tests for CLI workflows."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

from click.testing import CliRunner

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

commands = importlib.import_module("duplicate_image_detector.cli.main")
database = importlib.import_module("duplicate_image_detector.core.database")
CacheDB = database.CacheDB


def test_remove_group_and_restore_lifecycle(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()

    cache_db = tmp_path / "cache.db"
    monkeypatch.setattr(commands, "CACHE_DB_PATH", cache_db)

    # Create duplicate files and scan JSON with one group.
    keep_file = tmp_path / "keep.jpg"
    remove_file = tmp_path / "remove.jpg"
    keep_file.write_text("same-content")
    remove_file.write_text("same-content")

    scan_json = tmp_path / "scan.json"
    scan_json.write_text(
        json.dumps(
            {
                "exact_duplicates": [
                    {
                        "group_id": 1,
                        "files": [
                            {
                                "path": str(keep_file),
                                "size": keep_file.stat().st_size,
                                "mtime": keep_file.stat().st_mtime,
                            },
                            {
                                "path": str(remove_file),
                                "size": remove_file.stat().st_size,
                                "mtime": remove_file.stat().st_mtime,
                            },
                        ],
                    }
                ],
                "similar_images": [],
            }
        )
    )

    # Ensure deterministic keep strategy by making keep_file older.
    old_time = 1_000_000.0
    new_time = 2_000_000.0
    keep_file.touch()
    remove_file.touch()
    Path(keep_file).stat()
    Path(remove_file).stat()

    import os

    os.utime(keep_file, (old_time, old_time))
    os.utime(remove_file, (new_time, new_time))

    backup_dir = tmp_path / "backup"

    # Remove by group id, keeping oldest => remove newer file.
    result = runner.invoke(
        commands.app,
        [
            "remove",
            "--group-id",
            "1",
            "--input",
            str(scan_json),
            "--keep",
            "oldest",
            "--backup",
            "--backup-dir",
            str(backup_dir),
        ],
    )
    assert result.exit_code == 0, result.output
    assert keep_file.exists()
    assert not remove_file.exists()

    # Verify journal entry persisted.
    db = CacheDB(cache_db)
    try:
        entries = db.list_recent_deletions(limit=10)
        assert len(entries) == 1
        assert entries[0]["original"] == str(remove_file)
    finally:
        db.close()

    # Restore and verify file comes back.
    restore_result = runner.invoke(commands.app, ["restore", "--limit", "10"])
    assert restore_result.exit_code == 0, restore_result.output
    assert remove_file.exists()

    db = CacheDB(cache_db)
    try:
        entries_after = db.list_recent_deletions(limit=10)
        assert entries_after == []
    finally:
        db.close()


def test_restore_dry_run_keeps_backup_files(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()

    cache_db = tmp_path / "cache.db"
    monkeypatch.setattr(commands, "CACHE_DB_PATH", cache_db)

    original = tmp_path / "photo.jpg"
    original.write_text("photo")
    backup = tmp_path / "backup" / "photo.jpg"
    backup.parent.mkdir(parents=True, exist_ok=True)
    original.replace(backup)

    db = CacheDB(cache_db)
    try:
        db.record_deletions([(str(original), str(backup))])
    finally:
        db.close()

    result = runner.invoke(commands.app, ["restore", "--limit", "5", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert backup.exists()
    assert not original.exists()


def test_remove_mixed_targets_and_group_id_dedupes(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()

    cache_db = tmp_path / "cache.db"
    monkeypatch.setattr(commands, "CACHE_DB_PATH", cache_db)

    keep_file = tmp_path / "keep.jpg"
    dup_file = tmp_path / "dup.jpg"
    explicit_target = tmp_path / "explicit.jpg"
    keep_file.write_text("same")
    dup_file.write_text("same")
    explicit_target.write_text("other")

    import os

    old_time = 1_000_000.0
    new_time = 2_000_000.0
    os.utime(keep_file, (old_time, old_time))
    os.utime(dup_file, (new_time, new_time))

    scan_json = tmp_path / "scan.json"
    scan_json.write_text(
        json.dumps(
            {
                "exact_duplicates": [
                    {
                        "group_id": 9,
                        "files": [
                            {
                                "path": str(keep_file),
                                "size": keep_file.stat().st_size,
                                "mtime": keep_file.stat().st_mtime,
                            },
                            {
                                "path": str(dup_file),
                                "size": dup_file.stat().st_size,
                                "mtime": dup_file.stat().st_mtime,
                            },
                        ],
                    }
                ],
                "similar_images": [],
            }
        )
    )

    backup_dir = tmp_path / "backup"

    # Pass dup_file explicitly and via --group-id at same time; it should be removed once.
    result = runner.invoke(
        commands.app,
        [
            "remove",
            str(dup_file),
            str(explicit_target),
            "--group-id",
            "9",
            "--input",
            str(scan_json),
            "--keep",
            "oldest",
            "--backup",
            "--backup-dir",
            str(backup_dir),
        ],
    )
    assert result.exit_code == 0, result.output
    assert keep_file.exists()
    assert not dup_file.exists()
    assert not explicit_target.exists()

    db = CacheDB(cache_db)
    try:
        entries = db.list_recent_deletions(limit=10)
        # Should have exactly two records: dup_file (once) and explicit_target.
        originals = sorted(e["original"] for e in entries)
        assert originals == sorted([str(dup_file), str(explicit_target)])
    finally:
        db.close()


def test_remove_group_id_requires_input(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()

    cache_db = tmp_path / "cache.db"
    monkeypatch.setattr(commands, "CACHE_DB_PATH", cache_db)

    result = runner.invoke(commands.app, ["remove", "--group-id", "1"])
    assert result.exit_code == 0
    assert "--group-id requires --input" in result.output
