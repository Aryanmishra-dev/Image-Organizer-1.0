"""Safe deletion and backup routines."""

from __future__ import annotations

import shutil
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DeletionRecord:
    original: Path
    backup: Path


class Cleaner:
    """Handles dry-run deletion and optional backups."""

    def __init__(self, backup_dir: Path | None = None) -> None:
        self.backup_dir = backup_dir or Path.home() / ".dupclean_backup"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.history: list[DeletionRecord] = []

    def dry_run(self, targets: Iterable[Path]) -> list[Path]:
        return list(targets)

    def delete_with_backup(self, targets: Iterable[Path]) -> list[DeletionRecord]:
        records: list[DeletionRecord] = []
        for path in targets:
            if not path.exists():
                continue
            destination = self._unique_backup_path(path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), destination)
            record = DeletionRecord(original=path, backup=destination)
            self.history.append(record)
            records.append(record)
        return records

    def undo_latest(self) -> None:
        # Restore in reverse order to handle nested paths.
        while self.history:
            record = self.history.pop()
            record.original.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(record.backup), record.original)

    def restore_records(self, records: Iterable[DeletionRecord]) -> list[DeletionRecord]:
        restored: list[DeletionRecord] = []
        for record in records:
            if not record.backup.exists():
                continue
            record.original.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(record.backup), record.original)
            restored.append(record)
        return restored

    def _unique_backup_path(self, path: Path) -> Path:
        candidate = self.backup_dir / path.relative_to(path.anchor)
        idx = 0
        while candidate.exists():
            idx += 1
            candidate = candidate.with_name(f"{candidate.name}.{idx}")
        return candidate
