"""Tests for core.database – SQLite cache layer."""
from __future__ import annotations

from pathlib import Path

from core.database import CacheDB


def test_upsert_and_retrieve(tmp_path: Path) -> None:
    db = CacheDB(tmp_path / "test.db")
    try:
        db.upsert_file(Path("/a/file.txt"), 100, 1234.0, "abc123", "phash1")
        mtime_map = db.get_mtime_map([Path("/a/file.txt")])
        assert mtime_map["/a/file.txt"] == 1234.0
    finally:
        db.close()


def test_upsert_updates_existing(tmp_path: Path) -> None:
    db = CacheDB(tmp_path / "test.db")
    try:
        db.upsert_file(Path("/a/file.txt"), 100, 1000.0, "hash_v1", None)
        db.upsert_file(Path("/a/file.txt"), 200, 2000.0, "hash_v2", "phash2")

        mtime_map = db.get_mtime_map([Path("/a/file.txt")])
        assert mtime_map["/a/file.txt"] == 2000.0
    finally:
        db.close()


def test_get_mtime_map_empty(tmp_path: Path) -> None:
    db = CacheDB(tmp_path / "test.db")
    try:
        result = db.get_mtime_map([])
        assert result == {}
    finally:
        db.close()


def test_record_deletions(tmp_path: Path) -> None:
    db = CacheDB(tmp_path / "test.db")
    try:
        db.record_deletions([
            ("/original/a.txt", "/backup/a.txt"),
            ("/original/b.txt", "/backup/b.txt"),
        ])
        # Verify records exist (query the table directly)
        cur = db.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM deletions")
        assert cur.fetchone()[0] == 2
    finally:
        db.close()


def test_db_creates_parent_dirs(tmp_path: Path) -> None:
    db_path = tmp_path / "deep" / "nested" / "cache.db"
    db = CacheDB(db_path)
    try:
        assert db_path.parent.exists()
    finally:
        db.close()


def test_get_file_records_returns_hashes(tmp_path: Path) -> None:
    db = CacheDB(tmp_path / "test.db")
    try:
        db.upsert_file(Path("/a/file.txt"), 300, 777.0, "sha", "phash")
        records = db.get_file_records([Path("/a/file.txt")])

        assert records["/a/file.txt"]["size"] == 300
        assert records["/a/file.txt"]["mtime"] == 777.0
        assert records["/a/file.txt"]["sha256"] == "sha"
        assert records["/a/file.txt"]["phash"] == "phash"
    finally:
        db.close()


def test_upsert_files_bulk(tmp_path: Path) -> None:
    db = CacheDB(tmp_path / "test.db")
    try:
        db.upsert_files(
            [
                (Path("/a/one.txt"), 10, 1.0, "h1", None),
                (Path("/a/two.txt"), 20, 2.0, "h2", "p2"),
            ]
        )
        records = db.get_file_records([Path("/a/one.txt"), Path("/a/two.txt")])
        assert records["/a/one.txt"]["sha256"] == "h1"
        assert records["/a/two.txt"]["phash"] == "p2"
    finally:
        db.close()
