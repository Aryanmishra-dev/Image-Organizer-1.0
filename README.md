# DupClean

Professional-grade duplicate file cleaner for macOS (optimized for Apple Silicon). Provides high-speed exact and perceptual duplicate detection, safe cleanup workflows, and both GUI (PyQt6) and CLI (Click) interfaces.

## Status
Scaffolding in progress. Core modules stubbed with TODOs for hashing, scanning, comparison, GUI, and CLI wiring.

## Quick start (dev)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/main.py --help
```

## Features (planned)
- Exact, perceptual, and fuzzy duplicate detection
- Multiprocessing and batch scanning for large datasets
- SQLite caching for incremental scans and undo history
- PyQt6 GUI with preview/selection, Click-based CLI
- Safe cleanup: dry-run, trash/backup, undo window

## Repo layout
See src/ for implementation, tests/ for unit tests, resources/ for config and assets, docs/ for guides.
