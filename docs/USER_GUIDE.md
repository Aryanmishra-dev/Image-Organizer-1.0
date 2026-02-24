# Image Organizer — User Guide

A comprehensive guide to installing, configuring, and using Image Organizer.

---

## Table of Contents

1. [Installation](#installation)
2. [Configuration](#configuration)
3. [CLI Usage](#cli-usage)
4. [GUI Usage](#gui-usage)
5. [Duplicate Detection Strategies](#duplicate-detection-strategies)
6. [Safe Cleanup & Undo](#safe-cleanup--undo)
7. [Reporting](#reporting)
8. [Performance Tuning](#performance-tuning)
9. [Troubleshooting](#troubleshooting)

---

## Installation

### Prerequisites

- macOS 12+ (optimized for Apple Silicon)
- Python 3.11 or later

### Steps

```bash
# Clone and enter the repository
git clone https://github.com/theogengineer/Image-Organizer-1.0.git
cd Image-Organizer-1.0

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install production dependencies
pip install -r requirements.txt

# (Optional) Install as editable package
pip install -e .
```

---

## Configuration

Image Organizer uses YAML configuration. The default config is at `resources/config.default.yaml`.

### Key Settings

```yaml
scan:
  extensions:
    - .jpg
    - .jpeg
    - .png
    - .gif
    - .bmp
    - .tiff
    - .webp
    - .heic
  min_size: 1024          # Skip files smaller than 1 KB
  follow_symlinks: false

detection:
  hash_algorithm: sha256  # Options: sha256, xxhash
  perceptual_threshold: 10  # Hamming distance (lower = stricter)

performance:
  max_workers: null       # null = auto-detect CPU count
  batch_size: 1000

safety:
  backup_enabled: true
  backup_dir: ~/.image-organizer/backups
  dry_run: false
```

To use a custom config:

```bash
export IMAGE_ORGANIZER_CONFIG=/path/to/my-config.yaml
```

Or place a `config.yaml` in the project root.

---

## CLI Usage

All commands are accessed via the Click CLI:

```bash
cd src
python -m cli.commands --help
```

### Scan for Duplicates

```bash
# Scan one or more directories
python -m cli.commands scan ~/Pictures ~/Downloads

# Scan only images
python -m cli.commands scan ~/Photos --type images

# Save results to JSON
python -m cli.commands scan ~/Photos -o results.json
```

The scan command displays a Rich progress bar and summary table.

### Remove Duplicates

```bash
# Preview what would be removed (dry run)
python -m cli.commands remove /path/to/file.jpg --dry-run

# Remove with automatic backup
python -m cli.commands remove /path/to/file.jpg --backup

# Remove without backup (permanent)
python -m cli.commands remove /path/to/file.jpg
```

### Generate Reports

```bash
# JSON report
python -m cli.commands report -i results.json -o report.json -f json

# CSV report
python -m cli.commands report -i results.json -o report.csv -f csv
```

### System Info

```bash
python -m cli.commands info
```

Displays Python version, platform, CPU count, and available disk space.

---

## GUI Usage

Launch the PyQt6 graphical interface:

```bash
cd src && python -m cli.commands gui
```

### Dashboard View

The home screen shows:
- **Stat Cards**: Total files scanned, duplicates found, space reclaimable, active scans
- **Quick Actions**: One-click buttons for common tasks
- **Drag & Drop**: Drop folders directly onto the window to scan

### Scan View

Configure and launch scans:
1. Select target directories
2. Choose detection mode (exact, perceptual, or both)
3. Click **Start Scan** — progress is shown in real-time

### Results View

Review and act on findings:
- Grouped duplicate sets with thumbnails
- AI agent recommendations (which file to keep)
- Bulk select/deselect for cleanup
- Preview dialog for side-by-side comparison

### Settings View

Adjust configuration:
- Similarity threshold slider
- Hash algorithm selection
- Backup preferences
- Worker count for performance tuning

---

## Duplicate Detection Strategies

Image Organizer employs three complementary strategies:

### 1. Exact Hash Matching

Computes SHA-256 or xxHash digests. Files with identical hashes are guaranteed byte-identical duplicates. This is the fastest and most precise method.

### 2. Perceptual Hash Matching

Uses pHash, dHash, and average hash algorithms to detect **visually similar** images even when they differ in:
- Resolution or dimensions
- Compression level (quality)
- Minor color adjustments
- Format conversion (JPEG → PNG)

Similarity is measured by Hamming distance. The default threshold of 10 catches most near-duplicates while avoiding false positives.

### 3. AI Agent Scoring

The rule-based agent scores each file in a duplicate group on multiple factors:
- **Resolution** — higher resolution scores better
- **File size** — larger (higher quality) preferred
- **Modification time** — newer files score higher
- **Location** — files in preferred folders get a bonus
- **Format** — lossless formats (PNG, TIFF) preferred over lossy (JPEG)
- **Metadata** — files with complete EXIF data score better

The highest-scoring file is recommended as the "keeper."

---

## Safe Cleanup & Undo

Image Organizer never permanently deletes files by default:

1. **Dry Run Mode** — preview all deletions without modifying anything
2. **Automatic Backup** — files are copied to a backup directory before removal
3. **Undo** — restore the most recent batch of deletions with one command
4. **Deletion History** — all deletions are logged in the SQLite database

---

## Reporting

Export scan results in two formats:

- **JSON** — full structured data including hashes, scores, and metadata
- **CSV** — flat tabular format for spreadsheet analysis

Reports include: file paths, sizes, hash values, duplicate group IDs, and agent recommendations.

---

## Performance Tuning

### Worker Count

By default, the hasher uses all available CPU cores. Override with:

```yaml
performance:
  max_workers: 4  # Limit to 4 parallel workers
```

Or set the environment variable:

```bash
export MAX_WORKERS=4
```

### Batch Size

The scanner processes files in batches to manage memory:

```yaml
performance:
  batch_size: 2000  # Default: 1000
```

### Incremental Scanning

After the first scan, subsequent scans use the SQLite cache to skip unchanged files. This provides a **95%+ cache hit ratio** on repeat scans.

---

## Troubleshooting

### Common Issues

| Issue                          | Solution                                          |
| ------------------------------ | ------------------------------------------------- |
| `ModuleNotFoundError: PyQt6`   | Run `pip install -r requirements.txt`             |
| GUI doesn't launch             | Ensure you're in `src/` directory                 |
| Slow perceptual hashing        | Reduce worker count or increase batch size        |
| Permission denied on scan      | Check folder permissions with `ls -la`            |
| Database locked                | Close other instances of Image Organizer          |

### Getting Help

- Check the [API Reference](API_REFERENCE.md) for detailed module docs
- Open an [issue on GitHub](https://github.com/theogengineer/Image-Organizer-1.0/issues)
