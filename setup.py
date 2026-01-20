from setuptools import find_packages, setup

setup(
    name="dupclean",
    version="0.1.0",
    description="High-performance duplicate cleaner for macOS",
    author="",
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
        "dev": ["pytest>=7.4.4"],
    },
    entry_points={
        "console_scripts": [
            "dupclean=cli.commands:app",
        ]
    },
)
