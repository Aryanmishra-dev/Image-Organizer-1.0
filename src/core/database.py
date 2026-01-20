"""SQLite caching for hashes and history."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Optional


class CacheDB:
    def __init__(self, path: Path | str = "dupclean.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS files (
                path TEXT PRIMARY KEY,
                size INTEGER,
                mtime REAL,
                sha256 TEXT,
                phash TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS deletions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original TEXT,
                backup TEXT,
                deleted_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.conn.commit()

    def upsert_file(self, path: Path, size: int, mtime: float, sha256: Optional[str], phash: Optional[str]) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO files(path, size, mtime, sha256, phash)
            VALUES(?,?,?,?,?)
            ON CONFLICT(path) DO UPDATE SET size=excluded.size, mtime=excluded.mtime, sha256=excluded.sha256, phash=excluded.phash
            """,
            (str(path), size, mtime, sha256, phash),
        )
        self.conn.commit()

    def get_mtime_map(self, paths: Iterable[Path]) -> dict[str, float]:
        placeholders = ",".join("?" for _ in paths)
        items = list(paths)
        if not items:
            return {}
        cur = self.conn.cursor()
        cur.execute(f"SELECT path, mtime FROM files WHERE path IN ({placeholders})", [str(p) for p in items])
        return {row[0]: row[1] for row in cur.fetchall()}

    def record_deletions(self, records: Iterable[tuple[str, str]]) -> None:
        cur = self.conn.cursor()
        cur.executemany(
            "INSERT INTO deletions(original, backup) VALUES(?,?)",
            records,
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
