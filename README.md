<div align="center">

# 🖼️ Image Organizer

**AI-powered duplicate image detection and intelligent file organization for macOS**

[![CI Pipeline](https://github.com/theogengineer/Image-Organizer-1.0/actions/workflows/ci.yml/badge.svg)](https://github.com/theogengineer/Image-Organizer-1.0/actions/workflows/ci.yml)
[![CodeQL](https://github.com/theogengineer/Image-Organizer-1.0/actions/workflows/codeql.yml/badge.svg)](https://github.com/theogengineer/Image-Organizer-1.0/actions/workflows/codeql.yml)
[![codecov](https://codecov.io/gh/theogengineer/Image-Organizer-1.0/branch/main/graph/badge.svg)](https://codecov.io/gh/theogengineer/Image-Organizer-1.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://pre-commit.com/)

<br/>

<img src="https://img.shields.io/badge/macOS-000000?logo=apple&logoColor=white" alt="macOS" />
<img src="https://img.shields.io/badge/Apple%20Silicon-optimized-red?logo=apple" alt="Apple Silicon" />
<img src="https://img.shields.io/badge/PyQt6-GUI-41CD52?logo=qt" alt="PyQt6" />

</div>

---

## Problem Statement

Digital photo libraries grow rapidly, often accumulating **thousands of duplicate and near-duplicate images** across downloads, backups, and synced folders. Manually identifying and cleaning them is tedious, error-prone, and risks deleting the wrong copy.

**Image Organizer** solves this with a multi-strategy detection engine that combines exact hashing, perceptual similarity analysis, and an intelligent rule-based agent — all wrapped in a modern GUI and a powerful CLI.

---

## Tech Stack

| Layer         | Technology                                    |
| ------------- | --------------------------------------------- |
| Language      | Python 3.11+                                  |
| GUI           | PyQt6 (dark theme, WCAG 2.1 AA compliant)     |
| CLI           | Click + Rich (progress bars, tables, panels)   |
| Hashing       | SHA-256, xxHash (xxh3_128), pHash, dHash, aHash |
| Image AI      | Pillow + imagehash (perceptual comparison)     |
| Cache         | SQLite (incremental scans, undo history)       |
| Parallelism   | multiprocessing.ProcessPoolExecutor            |
| Config        | YAML (PyYAML)                                  |
| Testing       | pytest + pytest-cov + pytest-xdist             |
| Linting       | Ruff, Black, MyPy, Bandit                      |
| CI/CD         | GitHub Actions (matrix builds, CodeQL)         |

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                     User Interface                    │
│        ┌──────────────┐    ┌──────────────┐          │
│        │   PyQt6 GUI  │    │   Click CLI  │          │
│        └──────┬───────┘    └──────┬───────┘          │
│               │                   │                   │
├───────────────┼───────────────────┼──────────────────┤
│               ▼                   ▼                   │
│        ┌──────────────────────────────────┐          │
│        │         Core Engine              │          │
│        │  ┌─────────┐  ┌──────────────┐  │          │
│        │  │ Scanner  │  │   Hasher     │  │          │
│        │  │ (batch)  │  │ (parallel)   │  │          │
│        │  └────┬─────┘  └──────┬───────┘  │          │
│        │       │               │          │          │
│        │  ┌────▼───────────────▼───────┐  │          │
│        │  │      Comparator            │  │          │
│        │  │  (exact + perceptual)      │  │          │
│        │  └────────────┬───────────────┘  │          │
│        │               │                  │          │
│        │  ┌────────────▼───────────────┐  │          │
│        │  │     AI Agent (scoring)     │  │          │
│        │  └────────────┬───────────────┘  │          │
│        │               │                  │          │
│        │  ┌────────────▼───────────────┐  │          │
│        │  │  Cleaner (backup + undo)   │  │          │
│        │  └────────────────────────────┘  │          │
│        └──────────────────────────────────┘          │
│                        │                              │
├────────────────────────┼─────────────────────────────┤
│        ┌───────────────▼──────────────────┐          │
│        │   SQLite Cache  │  YAML Config   │          │
│        └──────────────────────────────────┘          │
└──────────────────────────────────────────────────────┘
```

### Module Map

| Module              | Responsibility                                         |
| ------------------- | ------------------------------------------------------ |
| `core/scanner.py`   | Batched filesystem traversal with filtering             |
| `core/hasher.py`    | Parallel multi-algorithm hashing (SHA-256, xxHash, pHash) |
| `core/comparator.py`| Duplicate grouping (exact, perceptual, size-based)      |
| `core/agent.py`     | Rule-based scoring engine for keep/remove decisions     |
| `core/cleaner.py`   | Safe deletion with backup and undo                      |
| `core/database.py`  | SQLite cache for incremental scans                      |
| `gui/main_window.py`| Full PyQt6 GUI (dashboard, scan, results, settings)     |
| `cli/commands.py`   | Click CLI with Rich output                              |
| `utils/config.py`   | YAML configuration loader                               |
| `utils/logger.py`   | Rotating file + console logging                         |
| `utils/reporter.py` | JSON/CSV report generation                              |

---

## Installation

### Prerequisites

- **Python 3.11+**
- **macOS** (optimized for Apple Silicon, works on Intel)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/theogengineer/Image-Organizer-1.0.git
cd Image-Organizer-1.0

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# (Optional) Install dev dependencies
make dev
```

### Install as Package

```bash
pip install -e .
```

---

## Usage

### CLI

```bash
# Scan directories for duplicates
cd src && python -m cli.commands scan ~/Pictures ~/Downloads --type images

# Scan with JSON output
python -m cli.commands scan ~/Pictures -o results.json

# Remove duplicates (with backup)
python -m cli.commands remove /path/to/duplicate.jpg --backup

# Dry run (preview what would be deleted)
python -m cli.commands remove /path/to/file.jpg --dry-run

# Generate report from previous scan
python -m cli.commands report -i results.json -o report.csv -f csv

# Show system info
python -m cli.commands info
```

### GUI

```bash
# Launch the graphical interface
cd src && python -m cli.commands gui

# Or directly
cd src && python -c "from gui.main_window import run_gui; run_gui()"
```

### Make Commands

```bash
make help         # Show all available commands
make run-cli      # Run CLI
make run-gui      # Launch GUI
make check        # Run all quality checks
make test-cov     # Run tests with coverage
```

---

## Testing

```bash
# Run all tests
make test

# Run with coverage report
make test-cov

# Run tests in parallel (faster)
make test-fast

# Run specific test file
pytest tests/test_scanner.py -v
```

### Test Coverage Target: **80%+**

Coverage reports are generated in `htmlcov/` and uploaded to [Codecov](https://codecov.io/gh/theogengineer/Image-Organizer-1.0) via CI.

---

## CI/CD Pipeline

Every push and pull request triggers the following automated pipeline:

| Job              | Description                              |
| ---------------- | ---------------------------------------- |
| **Lint & Format** | Black formatting + Ruff linting + MyPy   |
| **Security Scan** | Bandit SAST + Safety dependency check    |
| **Test (matrix)** | pytest on Python 3.11/3.12 × Ubuntu/macOS |
| **Build**         | Package build verification               |
| **CodeQL**        | GitHub security analysis (weekly + PRs)  |

All checks must pass before merging to `main`.

---

## Performance

| Metric               | Value                          |
| -------------------- | ------------------------------ |
| Scan speed           | ~10,000 files/sec (SSD)       |
| Hash throughput      | ~500 MB/s (SHA-256, parallel)  |
| Perceptual comparison | O(n²) with Union-Find clustering |
| Memory usage         | ~50 MB base + streaming file I/O |
| Cache hit ratio      | 95%+ on incremental re-scans   |

Optimized for Apple Silicon with configurable worker count and batch sizes.

---

## Project Structure

```
Image-Organizer-1.0/
├── .github/
│   └── workflows/
│       ├── ci.yml              # Main CI pipeline
│       └── codeql.yml          # Security analysis
├── docs/
│   ├── API_REFERENCE.md        # Module API documentation
│   └── USER_GUIDE.md           # End-user guide
├── resources/
│   └── config.default.yaml     # Default configuration
├── src/
│   ├── cli/                    # Click CLI interface
│   ├── core/                   # Business logic engine
│   │   ├── agent.py            # AI scoring agent
│   │   ├── cleaner.py          # Safe deletion
│   │   ├── comparator.py       # Duplicate grouping
│   │   ├── database.py         # SQLite cache
│   │   ├── hasher.py           # Multi-algorithm hashing
│   │   └── scanner.py          # Filesystem traversal
│   ├── gui/                    # PyQt6 GUI
│   └── utils/                  # Config, logging, reporting
├── tests/                      # pytest test suite
├── .env.example                # Environment template
├── .pre-commit-config.yaml     # Pre-commit hooks
├── CHANGELOG.md                # Version history
├── CODE_OF_CONDUCT.md          # Community guidelines
├── CONTRIBUTING.md             # Contribution guide
├── LICENSE                     # MIT License
├── Makefile                    # Dev workflow commands
├── pyproject.toml              # Project config & tool settings
├── requirements.txt            # Production dependencies
└── requirements-dev.txt        # Development dependencies
```

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## Author

**Theo Engineer** — [@theogengineer](https://github.com/theogengineer)

---

## Contributing

Contributions are welcome! Please read the [Contributing Guide](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md) before submitting a PR.

---

<div align="center">
<sub>Built with precision. Engineered for production.</sub>
</div>
