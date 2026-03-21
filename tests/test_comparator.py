from pathlib import Path

from core.comparator import (
    DuplicateComparator,
    DuplicateType,
    similarity_percent_to_hamming_threshold,
)
from core.scanner import FileMetadata


def test_group_exact() -> None:
    files = [
        FileMetadata(path=Path("/a/file1.txt"), size=100, mtime=0, sha256="aaa"),
        FileMetadata(path=Path("/b/file2.txt"), size=100, mtime=0, sha256="aaa"),
        FileMetadata(path=Path("/c/file3.txt"), size=200, mtime=0, sha256="bbb"),
    ]
    groups = DuplicateComparator().group_by_exact_hash(files)
    assert len(groups) == 1
    assert groups[0].key == "aaa"
    assert groups[0].duplicate_type == DuplicateType.EXACT
    assert groups[0].count == 2


def test_group_wasted_size() -> None:
    files = [
        FileMetadata(path=Path("/a/f1.txt"), size=1000, mtime=0, sha256="x"),
        FileMetadata(path=Path("/b/f2.txt"), size=1000, mtime=0, sha256="x"),
        FileMetadata(path=Path("/c/f3.txt"), size=1000, mtime=0, sha256="x"),
    ]
    groups = DuplicateComparator().group_by_exact_hash(files)
    assert groups[0].total_size == 3000
    assert groups[0].wasted_size == 2000  # Can recover 2 copies


def test_get_original_strategies() -> None:
    files = [
        FileMetadata(path=Path("/old.txt"), size=100, mtime=1000, sha256="x"),
        FileMetadata(path=Path("/new.txt"), size=200, mtime=2000, sha256="x"),
    ]
    groups = DuplicateComparator().group_by_exact_hash(files)
    g = groups[0]

    assert g.get_original("oldest").path == Path("/old.txt")
    assert g.get_original("newest").path == Path("/new.txt")
    assert g.get_original("largest").path == Path("/new.txt")
    assert g.get_original("smallest").path == Path("/old.txt")


def test_similarity_percent_to_hamming_threshold() -> None:
    assert similarity_percent_to_hamming_threshold(100) == 0
    assert similarity_percent_to_hamming_threshold(90) == 6
    assert similarity_percent_to_hamming_threshold(70) == 19
    assert similarity_percent_to_hamming_threshold(0) == 64
