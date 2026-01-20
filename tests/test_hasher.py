from pathlib import Path

from core.hasher import compute_sha256, compute_xxhash, hamming_distance, hashes_are_similar


def test_sha256(tmp_path: Path) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("hello")
    digest = compute_sha256(file_path)
    assert len(digest) == 64


def test_xxhash(tmp_path: Path) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("hello world")
    digest = compute_xxhash(file_path)
    assert digest is not None
    assert len(digest) == 32  # xxh3_128 produces 32 hex chars


def test_identical_files_same_hash(tmp_path: Path) -> None:
    content = "identical content here"
    f1 = tmp_path / "file1.txt"
    f2 = tmp_path / "file2.txt"
    f1.write_text(content)
    f2.write_text(content)
    assert compute_sha256(f1) == compute_sha256(f2)


def test_hamming_distance() -> None:
    h1 = "ffffffff"
    h2 = "fffffffe"  # 1 bit different
    assert hamming_distance(h1, h2) == 1


def test_hashes_are_similar() -> None:
    assert hashes_are_similar("ffff", "ffff", threshold=0) is True
    assert hashes_are_similar("ffff", "fff0", threshold=4) is True
