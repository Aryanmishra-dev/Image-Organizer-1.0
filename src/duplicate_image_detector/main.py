"""Main entry point for DupClean."""

from __future__ import annotations

from duplicate_image_detector.cli.main import app


def run_cli() -> None:
    """Run the Click CLI."""
    app(prog_name="dupclean")


def main() -> None:
    """Entry point; defaults to CLI. GUI hook lives in gui.main_window."""
    run_cli()


if __name__ == "__main__":
    main()
