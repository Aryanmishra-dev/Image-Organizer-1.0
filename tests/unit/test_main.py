"""Tests for the package entrypoint module."""

from __future__ import annotations

import importlib


def test_run_cli_invokes_app_with_expected_program_name(monkeypatch) -> None:
    main_module = importlib.import_module("duplicate_image_detector.main")
    called: dict[str, str] = {}

    def _fake_app(*, prog_name: str) -> None:
        called["prog_name"] = prog_name

    monkeypatch.setattr(main_module, "app", _fake_app)

    main_module.run_cli()

    assert called["prog_name"] == "dupclean"


def test_main_delegates_to_run_cli(monkeypatch) -> None:
    main_module = importlib.import_module("duplicate_image_detector.main")
    called = {"run_cli": False}

    def _fake_run_cli() -> None:
        called["run_cli"] = True

    monkeypatch.setattr(main_module, "run_cli", _fake_run_cli)

    main_module.main()

    assert called["run_cli"] is True
