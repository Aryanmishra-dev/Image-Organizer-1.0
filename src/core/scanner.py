"""High-performance filesystem scanner with batching, filtering, and incremental support."""

from __future__ import annotations

import fnmatch
import os
import stat
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar


@dataclass
class FileMetadata:
    """Metadata for a scanned file."""

    path: Path
    size: int
    mtime: float
    inode: int = 0
    sha256: str | None = None
    xxhash: str | None = None
    phash: str | None = None

    def __hash__(self) -> int:
        return hash(str(self.path))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FileMetadata):
            return False
        return self.path == other.path


@dataclass
class ScanConfig:
    """Configuration for file scanning."""

    batch_size: int = 500
    follow_symlinks: bool = False
    ignore_hidden: bool = True
    min_size: int = 1  # Skip empty files
    max_size: int = 0  # 0 = no limit
    file_extensions: set[str] | None = None  # None = all files
    ignore_patterns: list[str] = field(
        default_factory=lambda: [
            ".git",
            ".svn",
            ".hg",
            "node_modules",
            "__pycache__",
            ".DS_Store",
            "Thumbs.db",
            ".Spotlight-V100",
            ".Trashes",
        ]
    )
    protected_paths: list[str] = field(
        default_factory=lambda: ["/System", "/Library", "/usr", "/bin", "/sbin"]
    )


class FileScanner:
    """Walks directories and yields file metadata in batches with filtering."""

    # Common file type extensions
    IMAGE_EXTENSIONS: ClassVar[set[str]] = {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".tiff",
        ".tif",
        ".webp",
        ".heic",
        ".heif",
        ".raw",
        ".cr2",
        ".nef",
        ".arw",
    }
    VIDEO_EXTENSIONS: ClassVar[set[str]] = {
        ".mp4",
        ".mov",
        ".avi",
        ".mkv",
        ".wmv",
        ".flv",
        ".webm",
        ".m4v",
        ".mpg",
        ".mpeg",
        ".3gp",
    }
    AUDIO_EXTENSIONS: ClassVar[set[str]] = {
        ".mp3",
        ".wav",
        ".flac",
        ".aac",
        ".ogg",
        ".wma",
        ".m4a",
        ".aiff",
        ".alac",
    }
    DOCUMENT_EXTENSIONS: ClassVar[set[str]] = {
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".txt",
        ".rtf",
        ".odt",
        ".ods",
        ".odp",
        ".pages",
        ".numbers",
    }

    def __init__(self, config: ScanConfig | None = None) -> None:
        self.config = config or ScanConfig()
        self._file_count = 0
        self._total_size = 0
        self._skipped_count = 0

    @property
    def stats(self) -> dict:
        """Return scan statistics."""
        return {
            "files_scanned": self._file_count,
            "total_size": self._total_size,
            "skipped": self._skipped_count,
        }

    def scan(
        self,
        roots: list[Path],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> Iterator[list[FileMetadata]]:
        """
        Yield lists of FileMetadata with size batch_size.

        Args:
            roots: List of directories or files to scan
            progress_callback: Optional callback(files_processed, total_size)
        """
        self._file_count = 0
        self._total_size = 0
        self._skipped_count = 0
        batch: list[FileMetadata] = []

        for file_path in self._iter_files(roots):
            try:
                stat_info = file_path.stat(follow_symlinks=self.config.follow_symlinks)
            except (OSError, PermissionError):
                self._skipped_count += 1
                continue

            # Skip non-regular files
            if not stat.S_ISREG(stat_info.st_mode):
                continue

            # Apply filters
            if not self._passes_filters(file_path, stat_info):
                self._skipped_count += 1
                continue

            meta = FileMetadata(
                path=file_path,
                size=stat_info.st_size,
                mtime=stat_info.st_mtime,
                inode=stat_info.st_ino,
            )
            batch.append(meta)
            self._file_count += 1
            self._total_size += stat_info.st_size

            if progress_callback:
                progress_callback(self._file_count, self._total_size)

            if len(batch) >= self.config.batch_size:
                yield batch
                batch = []

        if batch:
            yield batch

    def scan_for_size_groups(
        self,
        roots: list[Path],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> dict[int, list[FileMetadata]]:
        """
        First-pass scan: group files by size (potential duplicates).
        Only files with matching sizes need hash comparison.
        """
        size_groups: dict[int, list[FileMetadata]] = {}

        for batch in self.scan(roots, progress_callback):
            for meta in batch:
                if meta.size not in size_groups:
                    size_groups[meta.size] = []
                size_groups[meta.size].append(meta)

        # Return only groups with more than one file (potential duplicates)
        return {size: files for size, files in size_groups.items() if len(files) > 1}

    def incremental_scan(
        self,
        roots: list[Path],
        known_files: dict[str, tuple[float, int]],  # path -> (mtime, size)
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> Iterator[list[FileMetadata]]:
        """
        Scan only files that are new or modified since last scan.

        Args:
            roots: Directories to scan
            known_files: Dict of path -> (mtime, size) from previous scan
            progress_callback: Optional progress callback
        """
        self._file_count = 0
        self._total_size = 0
        self._skipped_count = 0
        batch: list[FileMetadata] = []

        for file_path in self._iter_files(roots):
            try:
                stat_info = file_path.stat(follow_symlinks=self.config.follow_symlinks)
            except (OSError, PermissionError):
                self._skipped_count += 1
                continue

            if not stat.S_ISREG(stat_info.st_mode):
                continue

            if not self._passes_filters(file_path, stat_info):
                self._skipped_count += 1
                continue

            # Check if file is unchanged
            path_str = str(file_path)
            if path_str in known_files:
                old_mtime, old_size = known_files[path_str]
                if stat_info.st_mtime == old_mtime and stat_info.st_size == old_size:
                    continue  # Skip unchanged file

            meta = FileMetadata(
                path=file_path,
                size=stat_info.st_size,
                mtime=stat_info.st_mtime,
                inode=stat_info.st_ino,
            )
            batch.append(meta)
            self._file_count += 1
            self._total_size += stat_info.st_size

            if progress_callback:
                progress_callback(self._file_count, self._total_size)

            if len(batch) >= self.config.batch_size:
                yield batch
                batch = []

        if batch:
            yield batch

    def _passes_filters(self, path: Path, stat_info: os.stat_result) -> bool:
        """Check if file passes all configured filters."""
        # Hidden file check
        if self.config.ignore_hidden and path.name.startswith("."):
            return False

        # Size filters
        if stat_info.st_size < self.config.min_size:
            return False
        if self.config.max_size > 0 and stat_info.st_size > self.config.max_size:
            return False

        # Extension filter
        if self.config.file_extensions is not None:
            ext = path.suffix.lower()
            if ext not in self.config.file_extensions:
                return False

        # Protected path check
        path_str = str(path)
        return all(not path_str.startswith(protected) for protected in self.config.protected_paths)

    def _iter_files(self, roots: list[Path]) -> Iterator[Path]:
        """Iterate through all files in given roots."""
        for root in roots:
            root_path = Path(root).resolve()

            if not root_path.exists():
                continue

            if root_path.is_file():
                yield root_path
                continue

            try:
                for dirpath, dirnames, filenames in os.walk(
                    root_path, followlinks=self.config.follow_symlinks
                ):
                    # Filter directories in-place to skip ignored patterns
                    dirnames[:] = [d for d in dirnames if not self._should_ignore(d, is_dir=True)]

                    for name in filenames:
                        if not self._should_ignore(name, is_dir=False):
                            yield Path(dirpath) / name

            except PermissionError:
                self._skipped_count += 1
                continue

    def _should_ignore(self, name: str, is_dir: bool) -> bool:
        """Check if a file or directory should be ignored."""
        if self.config.ignore_hidden and name.startswith("."):
            return True

        return any(fnmatch.fnmatch(name, pattern) for pattern in self.config.ignore_patterns)

    @classmethod
    def get_extensions_for_type(cls, file_type: str) -> set[str]:
        """Get file extensions for a given type."""
        type_map = {
            "images": cls.IMAGE_EXTENSIONS,
            "videos": cls.VIDEO_EXTENSIONS,
            "audio": cls.AUDIO_EXTENSIONS,
            "documents": cls.DOCUMENT_EXTENSIONS,
        }
        return type_map.get(file_type.lower(), set())


def format_size(size_bytes: int) -> str:
    """Format byte size to human readable string."""
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"
