"""Backwards-compatible setup.py — all config lives in pyproject.toml."""

from setuptools import find_packages, setup

setup(
    name="image-organizer",
    version="2.0.0",
    description="AI-powered duplicate image detection and intelligent file organization for macOS",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Theo Engineer",
    author_email="",
    url="https://github.com/theogengineer/Image-Organizer-1.0",
    license="MIT",
    python_requires=">=3.11",
    packages=find_packages("src"),
    package_dir={"": "src"},
    install_requires=[
        "click>=8.1.7",
        "PyQt6>=6.6.1",
        "Pillow>=10.2.0",
        "imagehash>=4.3.1",
        "opencv-python>=4.9.0.80",
        "xxhash>=3.4.1",
        "PyYAML>=6.0.1",
        "rich>=13.7.0",
        "python-dateutil>=2.9.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.4",
            "pytest-cov>=4.1.0",
            "pytest-xdist>=3.5.0",
            "ruff>=0.2.0",
            "black>=24.0",
            "mypy>=1.8.0",
            "bandit>=1.7.7",
            "pre-commit>=3.6.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "image-organizer=cli.commands:app",
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: MacOS X",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Graphics",
    ],
)
