# Duplicate Image Detector 🔍
> A fast and efficient Python tool to find, review, and manage duplicate images in your directories.

## Why I Built This
As a student working on various image classification assignments and personal photography portfolios, I quickly realized my hard drive was filling up with redundant datasets, backups, and edited variants of the same pictures. Managing these manually was tedious and prone to errors. I built the **Duplicate Image Detector** to automate the process of finding identical and visually similar images efficiently, using hashing and parallel processing, while ensuring I never accidentally deleted important files.

## Key Features
- **Fast Scanning & Hashing:** Quickly traverses deep directory structures and computes MD5/SHA256 image hashes.
- **Visual Similarity Detection:** Identifies not just exact bit-for-bit duplicates, but visually similar versions (e.g., resized or slightly compressed images).
- **Interactive GUI & CLI:** Use the command line for fast scripting or the interactive GUI to preview images before deletion.
- **Batched Deletion & Safety Modes:** Dry-run modes, safe-delete features, and reporting options to keep your files secure.
- **SQLite Database:** Tracks hashes and scans persistently so subsequent scans are blazing fast for unchanged files.

## Tech Stack
- **Python 3.8+**
- **PyQt6 / PySide6** (for the sleek graphical interface)
- **Pillow** (for image processing)
- **ImageHash** (for perceptual hashing)
- **SQLite3** (for local caching)
- **pytest** (for robust unit & integration testing)

## Installation & Usage

1. **Clone the repository:**
   ```bash
   git clone https://github.com/YourGitHub/Duplicate-Image-Detector.git
   cd Duplicate-Image-Detector
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the tool:**
   *CLI mode to scan a directory:*
   ```bash
   python src/main.py scan /path/to/your/images
   ```
   *GUI mode with preview:*
   ```bash
   python src/main.py gui
   ```

## Running Tests
Ensure your dependencies match `requirements-dev.txt`, then run:
```bash
python -m pytest tests/ -v
```

## Project Structure
```text
Duplicate-Image-Detector/
├── CHANGELOG.md              # Project history
├── LICENSE                   # Licensing bounds
├── Makefile                  # Build/test shortcuts
├── README.md                 # You are here
├── pyproject.toml            # Build / config metadata
├── requirements*.txt         # Dependencies
├── docs/                     # Documentation (API, User Guide, Backlog)
├── resources/                # Static assets and default config files
├── src/                      # Source code
│   ├── cli/                  # Command-line interface logic
│   ├── core/                 # Core engine (scanner, hasher, db, agent)
│   ├── gui/                  # Graphical interface components
│   ├── utils/                # Logging, configuration, reporting helpers
│   └── main.py               # Entry point
└── tests/                    # 66+ tests verifying expected behavior
```

## What I Learned / Challenges Solved
- **Concurrency & I/O Bound Tasks:** Computing hashes for thousands of high-res images bottlenecked my first prototype. Implementing a thread pool significantly improved processing times.
- **Architecture & Decoupling:** I separated the `core` logic from the `gui` and `cli`. This made unit testing the core functions much simpler and cleaner.
- **Database Caching:** Relying purely on Python dictionaries caused out-of-memory errors on massive datasets. Offloading state to a lightweight SQLite database handled scale effortlessly.

## Future Improvements
- Add support for finding duplicates based on EXIF metadata (e.g. timestamp clustering).
- Implement deep learning encoders (like simplified ResNet) for semantic image similarity without strict structural matches.
- Automated release pipelines using GitHub Actions.

---
