#!/usr/bin/env bash
set -e

echo "Building Duplicate Image Detector GUI..."

# Ensure we're in the project root
cd "$(dirname "$0")/../.."

# Install PyInstaller if not present
pip install pyinstaller

# Build the standalone executable
pyinstaller --name "Duplicate Image Detector" \
    --windowed \
    --onefile \
    --clean \
    --noconfirm \
    --add-data "config/default.yaml:config" \
    src/duplicate_image_detector/gui/main_window.py

echo "Build complete! Executable is in the dist/ directory."
