"""SQLite caching for hashes and history."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable, Optional


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

    def upsert_file(
        self,
        path: Path,
        size: int,
        mtime: float,
        sha256: Optional[str],
        phash: Optional[str],
    ) -> None:
        self.upsert_files([(path, size, mtime, sha256, phash)])

    def upsert_files(
        self,
        records: Iterable[tuple[Path, int, float, Optional[str], Optional[str]]],
    ) -> None:
        payload = [
            (str(path), size, mtime, sha256, phash)
            for path, size, mtime, sha256, phash in records
        ]
        if not payload:
            return

        cur = self.conn.cursor()
        cur.executemany(
            """
            INSERT INTO files(path, size, mtime, sha256, phash)
            VALUES(?,?,?,?,?)
            ON CONFLICT(path) DO UPDATE SET size=excluded.size, mtime=excluded.mtime, sha256=excluded.sha256, phash=excluded.phash
            """,
            payload,
        )
        self.conn.commit()

    def get_mtime_map(self, paths: Iterable[Path]) -> dict[str, float]:
        items = list(paths)
        if not items:
            return {}

        placeholders = ",".join("?" for _ in items)
        cur = self.conn.cursor()
        cur.execute(f"SELECT path, mtime FROM files WHERE path IN ({placeholders})", [str(p) for p in items])
        return {row[0]: row[1] for row in cur.fetchall()}

    def get_file_records(self, paths: Iterable[Path]) -> dict[str, dict[str, Any]]:
        items = list(paths)
        if not items:
            return {}

        placeholders = ",".join("?" for _ in items)
        cur = self.conn.cursor()
        cur.execute(
            f"SELECT path, size, mtime, sha256, phash FROM files WHERE path IN ({placeholders})",
            [str(p) for p in items],
        )
        rows = cur.fetchall()
        return {
            row[0]: {
                "size": row[1],
                "mtime": row[2],
                "sha256": row[3],
                "phash": row[4],
            }
            for row in rows
        }

    def record_deletions(self, records: Iterable[tuple[str, str]]) -> None:
        payload = list(records)
        if not payload:
            return

        cur = self.conn.cursor()
        cur.executemany(
            "INSERT INTO deletions(original, backup) VALUES(?,?)",
            payload,
        )
        self.conn.commit()

    def list_recent_deletions(self, limit: int = 50) -> list[dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, original, backup, deleted_at
            FROM deletions
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(1, limit),),
        )
        rows = cur.fetchall()
        return [
            {
                "id": row[0],
                "original": row[1],
                "backup": row[2],
                "deleted_at": row[3],
            }
            for row in rows
        ]

    def delete_deletion_records(self, ids: Iterable[int]) -> None:
        id_list = list(ids)
        if not id_list:
            return

        placeholders = ",".join("?" for _ in id_list)
        cur = self.conn.cursor()
        cur.execute(f"DELETE FROM deletions WHERE id IN ({placeholders})", id_list)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
