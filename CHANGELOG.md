# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2026-02-24

### Added
- Modern dark-themed PyQt6 GUI with dashboard, scan, results, and settings views
- AI-powered duplicate analysis agent with rule-based scoring engine
- Perceptual hash (pHash) comparison for visually similar image detection
- Multi-algorithm hashing: SHA-256, xxHash (xxh3_128), pHash, dHash, aHash
- High-performance parallel file hashing with multiprocessing
- Incremental scanning with SQLite-backed cache for fast re-scans
- Drag-and-drop folder selection in GUI
- Rich CLI with progress bars, tables, and colored output
- Comprehensive scan/remove/report/info CLI commands
- Safe deletion with automatic backup and undo capability
- JSON/CSV/Text report export functionality
- WCAG 2.1 AA compliant dark theme with accent color system
- CI/CD pipeline with GitHub Actions (lint, test, security, build)
- Pre-commit hooks for automated code quality enforcement
- Full test suite with pytest (scanner, hasher, comparator, cleaner, database, agent)
- Conventional Commits workflow
- Production-grade project structure and documentation

### Changed
- Rebranded from "DupClean" to "Image Organizer"
- Upgraded from basic scaffold to fully implemented feature set
- Replaced setup.py-only config with pyproject.toml
- Enhanced .gitignore for comprehensive coverage

### Security
- Added Bandit static analysis for security scanning
- Added CodeQL workflow for automated vulnerability detection
- Environment variable configuration with .env.example template
- No hardcoded credentials in codebase

---

## [0.1.0] - 2026-01-15

### Added
- Initial project scaffolding
- Core module stubs (scanner, hasher, comparator, cleaner, database)
- Basic Click CLI structure
- PyQt6 GUI placeholder
- YAML configuration system
- Unit test foundation

[2.0.0]: https://github.com/theogengineer/Image-Organizer-1.0/compare/v0.1.0...v2.0.0
[0.1.0]: https://github.com/theogengineer/Image-Organizer-1.0/releases/tag/v0.1.0
