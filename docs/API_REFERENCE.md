# Image Organizer — API Reference

Complete module-level documentation for the Image Organizer core engine.

---

## Table of Contents

- [core.scanner](#corescanner)
- [core.hasher](#corehasher)
- [core.comparator](#corecomparator)
- [core.agent](#coreagent)
- [core.cleaner](#corecleaner)
- [core.database](#coredatabase)
- [utils.config](#utilsconfig)
- [utils.logger](#utilslogger)
- [utils.reporter](#utilsreporter)
- [cli.commands](#clicommands)

---

## core.scanner

### `FileMetadata` (dataclass)

| Field        | Type            | Description                    |
| ------------ | --------------- | ------------------------------ |
| `path`       | `Path`          | Absolute file path             |
| `size`       | `int`           | File size in bytes             |
| `mtime`      | `float`         | Last-modified timestamp        |
| `suffix`     | `str`           | Lowercase file extension       |
| `name`       | `str`           | File name                      |

### `ScanConfig` (dataclass)

| Field             | Type            | Default  | Description                       |
| ----------------- | --------------- | -------- | --------------------------------- |
| `extensions`      | `set[str]`      | images   | File extensions to include        |
| `min_size`        | `int`           | `1024`   | Minimum file size (bytes)         |
| `max_size`        | `int \| None`   | `None`   | Maximum file size (bytes)         |
| `follow_symlinks` | `bool`          | `False`  | Whether to follow symbolic links  |

### `FileScanner`

```python
class FileScanner:
    def __init__(self, config: ScanConfig | None = None) -> None: ...
    def scan(self, directories: list[Path], batch_size: int = 1000) -> list[FileMetadata]: ...
    def scan_incremental(self, directories: list[Path], mtime_map: dict) -> list[FileMetadata]: ...
    def group_by_size(self, files: list[FileMetadata]) -> dict[int, list[FileMetadata]]: ...
```

- **`scan()`** — Walks directories in batches, filters by config, yields `FileMetadata`.
- **`scan_incremental()`** — Only returns files modified since last scan (uses mtime map from `CacheDB`).
- **`group_by_size()`** — Groups files by exact size for fast pre-filtering.

### `format_size(size_bytes: int) -> str`

Formats byte count into human-readable string (e.g., `"1.5 MB"`).

---

## core.hasher

### `ParallelHasher`

```python
class ParallelHasher:
    def __init__(self, max_workers: int | None = None) -> None: ...
    def hash_files(self, paths: list[Path], algorithm: str = "sha256") -> dict[Path, str]: ...
```

- **`hash_files()`** — Uses `ProcessPoolExecutor` for parallel hashing. Algorithms: `"sha256"`, `"xxhash"`.

### Standalone Functions

| Function                                   | Returns   | Description                          |
| ------------------------------------------ | --------- | ------------------------------------ |
| `compute_sha256(path: Path)`               | `str`     | SHA-256 hex digest                   |
| `compute_xxhash(path: Path)`               | `str`     | xxHash (xxh3_128) hex digest         |
| `compute_phash(path: Path, size: int = 8)` | `str`     | Perceptual hash (Pillow+imagehash)   |
| `compute_dhash(path: Path, size: int = 8)` | `str`     | Difference hash                      |
| `compute_average_hash(path: Path)`         | `str`     | Average hash                         |
| `hamming_distance(h1: str, h2: str)`       | `int`     | Bit-distance between two hex hashes  |
| `hashes_are_similar(h1, h2, threshold=10)` | `bool`    | Whether distance ≤ threshold         |

---

## core.comparator

### `DuplicateType` (Enum)

| Value         | Description                        |
| ------------- | ---------------------------------- |
| `EXACT`       | Byte-identical files               |
| `PERCEPTUAL`  | Visually similar images            |
| `SIZE_ONLY`   | Same size, unconfirmed content     |

### `DuplicateGroup` (dataclass)

| Field          | Type              | Description                       |
| -------------- | ----------------- | --------------------------------- |
| `group_id`     | `int`             | Unique group identifier           |
| `dup_type`     | `DuplicateType`   | Detection method                  |
| `files`        | `list[Path]`      | All files in the group            |
| `representative` | `Path`          | Best file to keep                 |
| `total_size`   | `int`             | Combined size of all files        |

### `DuplicateComparator`

```python
class DuplicateComparator:
    def __init__(self, hasher: ParallelHasher, threshold: int = 10) -> None: ...
    def find_exact_duplicates(self, files: list[FileMetadata]) -> list[DuplicateGroup]: ...
    def find_perceptual_duplicates(self, files: list[FileMetadata]) -> list[DuplicateGroup]: ...
    def find_all_duplicates(self, files: list[FileMetadata]) -> ComparisonResult: ...
```

### `ComparisonResult` (dataclass)

| Field          | Type                    | Description                    |
| -------------- | ----------------------- | ------------------------------ |
| `groups`       | `list[DuplicateGroup]`  | All detected duplicate groups  |
| `total_waste`  | `int`                   | Total bytes reclaimable        |
| `scan_time`    | `float`                 | Seconds elapsed                |

---

## core.agent

### `FileScore` (dataclass)

| Field     | Type    | Description                         |
| --------- | ------- | ----------------------------------- |
| `path`    | `Path`  | File path                           |
| `score`   | `float` | Composite keep-score (higher=keep)  |
| `reasons` | `list`  | Human-readable scoring breakdown    |

### `DuplicateAgent`

```python
class DuplicateAgent:
    def __init__(self, protected_folders: list[str] | None = None) -> None: ...
    def analyze_duplicates(self, groups: list[DuplicateGroup]) -> dict[int, list[FileScore]]: ...
    def execute_recommendations(self, analysis: dict, dry_run: bool = True) -> list[dict]: ...
```

Scoring factors: resolution, file size, modification time, folder location, format preference, metadata completeness.

---

## core.cleaner

### `DeletionRecord` (dataclass)

| Field           | Type        | Description                    |
| --------------- | ----------- | ------------------------------ |
| `original_path` | `Path`      | Path of deleted file           |
| `backup_path`   | `Path \| None` | Backup location (if backed up) |
| `size`          | `int`       | File size in bytes             |
| `timestamp`     | `datetime`  | When deletion occurred         |

### `Cleaner`

```python
class Cleaner:
    def __init__(self, backup_dir: Path | None = None) -> None: ...
    def delete_files(self, paths: list[Path], dry_run: bool = False, backup: bool = True) -> list[DeletionRecord]: ...
    def undo_last(self) -> list[Path]: ...
```

- **`delete_files()`** — Removes files with optional backup and dry-run.
- **`undo_last()`** — Restores files from the most recent deletion batch.

---

## core.database

### `CacheDB`

```python
class CacheDB:
    def __init__(self, db_path: Path | str = ":memory:") -> None: ...
    def upsert_file(self, path: str, size: int, mtime: float, hash_val: str) -> None: ...
    def get_file(self, path: str) -> dict | None: ...
    def get_mtime_map(self) -> dict[str, float]: ...
    def record_deletion(self, original: str, backup: str | None, size: int) -> None: ...
    def get_deletions(self) -> list[dict]: ...
    def close(self) -> None: ...
```

SQLite-backed cache with `files` and `deletions` tables. Thread-safe.

---

## utils.config

### `load_config(path: str | Path | None = None) -> dict`

Loads YAML configuration. Falls back to `resources/config.default.yaml`. Returns merged dict.

---

## utils.logger

### `init_logging(level: str = "INFO", log_file: str | None = None) -> logging.Logger`

Configures root logger with console output and optional `RotatingFileHandler` (10 MB, 5 backups). Idempotent.

---

## utils.reporter

### `write_json(data: list[dict], output_path: str | Path) -> Path`

Writes scan/analysis results to a pretty-printed JSON file.

### `write_csv(data: list[dict], output_path: str | Path) -> Path`

Writes tabular results to CSV. Auto-detects fieldnames from first record.

---

## cli.commands

Click command group with the following subcommands:

| Command   | Description                                    |
| --------- | ---------------------------------------------- |
| `scan`    | Scan directories for duplicates                |
| `remove`  | Remove a file (with backup/dry-run options)    |
| `report`  | Generate JSON or CSV report from scan results  |
| `gui`     | Launch the PyQt6 graphical interface           |
| `info`    | Display system and environment information     |
