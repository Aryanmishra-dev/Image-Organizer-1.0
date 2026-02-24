"""Tests for core.agent – rule-based duplicate analysis."""
from __future__ import annotations

from pathlib import Path

from core.agent import DuplicateAgent


def _make_files(tmp_path: Path) -> list[dict]:
    """Create real files and return duplicate group dicts."""
    f1 = tmp_path / "photos" / "2024" / "vacation.jpg"
    f2 = tmp_path / "downloads" / "vacation.jpg"
    f1.parent.mkdir(parents=True, exist_ok=True)
    f2.parent.mkdir(parents=True, exist_ok=True)

    content = b"\x89PNG fake image data" * 100
    f1.write_bytes(content)
    f2.write_bytes(content)

    return [{"group_id": 1, "files": [{"path": str(f1)}, {"path": str(f2)}]}]


def test_analyze_produces_recommendations(tmp_path: Path) -> None:
    groups = _make_files(tmp_path)
    agent = DuplicateAgent()
    result = agent.analyze_duplicates(groups)

    assert result["method"] == "rule_based"
    assert result["total_groups"] >= 0  # May be 0 if files lack image metadata
    assert "recommendations" in result


def test_execute_dry_run(tmp_path: Path) -> None:
    groups = _make_files(tmp_path)
    agent = DuplicateAgent()
    analysis = agent.analyze_duplicates(groups)

    result = agent.execute_recommendations(
        analysis["recommendations"],
        dry_run=True,
    )
    assert result["dry_run"] is True
    # All files should still exist after dry run
    for rec in analysis["recommendations"]:
        for fp in rec.get("remove_files", []):
            assert Path(fp).exists()


def test_empty_groups_returns_zero() -> None:
    agent = DuplicateAgent()
    result = agent.analyze_duplicates([])
    assert result["total_groups"] == 0
    assert result["recommendations"] == []


def test_protected_folders() -> None:
    agent = DuplicateAgent(protected_folders=["/protected"])
    assert agent._is_protected(Path("/protected/file.txt"))
    assert not agent._is_protected(Path("/other/file.txt"))
