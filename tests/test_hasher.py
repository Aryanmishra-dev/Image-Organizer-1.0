from pathlib import Path
from typing import Any, cast

import pytest
from PIL import Image

import core.hasher as hasher_module
from core.hasher import (
    HAS_IMAGEHASH,
    HAS_XXHASH,
    HashResult,
    ParallelHasher,
    _hash_single_file,
    compute_average_hash,
    compute_dhash,
    compute_phash,
    compute_sha256,
    compute_xxhash,
    hamming_distance,
    hashes_are_similar,
)
from core.scanner import FileMetadata


def _write_test_image(path: Path, mode: str = "RGB") -> None:
    if mode == "RGBA":
        color = (255, 0, 0, 255)
    else:
        color = (255, 0, 0)
    image = Image.new(mode, (32, 32), color=color)
    image.save(path)


def test_sha256(tmp_path: Path) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("hello")
    digest = compute_sha256(file_path)
    assert len(digest) == 64


def test_xxhash(tmp_path: Path) -> None:
    if not HAS_XXHASH:
        pytest.skip("xxhash is not available in this environment")

    file_path = tmp_path / "file.txt"
    file_path.write_text("hello world")
    digest = compute_xxhash(file_path)
    assert digest is not None
    assert len(digest) == 32  # xxh3_128 produces 32 hex chars


def test_xxhash_returns_none_when_disabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("hello world")

    monkeypatch.setattr(hasher_module, "HAS_XXHASH", False)

    assert compute_xxhash(file_path) is None


def test_image_hash_functions_on_rgba_image(tmp_path: Path) -> None:
    if not HAS_IMAGEHASH:
        pytest.skip("imagehash is not available in this environment")

    file_path = tmp_path / "image.png"
    _write_test_image(file_path, mode="RGBA")

    assert compute_phash(file_path, hash_size=8) is not None
    assert compute_dhash(file_path, hash_size=8) is not None
    assert compute_average_hash(file_path, hash_size=8) is not None


def test_image_hash_functions_return_none_for_non_image(tmp_path: Path) -> None:
    file_path = tmp_path / "not-image.txt"
    file_path.write_text("this is not an image")

    assert compute_phash(file_path) is None
    assert compute_dhash(file_path) is None
    assert compute_average_hash(file_path) is None


def test_image_hash_functions_return_none_when_feature_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    file_path = tmp_path / "image.png"
    _write_test_image(file_path)

    monkeypatch.setattr(hasher_module, "HAS_IMAGEHASH", False)

    assert compute_phash(file_path) is None
    assert compute_dhash(file_path) is None
    assert compute_average_hash(file_path) is None


def test_hash_single_file_populates_hashes(tmp_path: Path) -> None:
    file_path = tmp_path / "photo.jpg"
    if HAS_IMAGEHASH:
        _write_test_image(file_path)
    else:
        file_path.write_bytes(b"not-an-image")

    result = _hash_single_file((file_path, True, True))

    assert result.path == file_path
    assert result.error is None
    assert result.sha256 is not None
    if HAS_XXHASH:
        assert result.xxhash is not None
    if HAS_IMAGEHASH:
        assert result.phash is not None


def test_hash_single_file_skips_perceptual_for_non_images(tmp_path: Path) -> None:
    file_path = tmp_path / "document.txt"
    file_path.write_text("hello")

    result = _hash_single_file((file_path, True, False))

    assert result.error is None
    assert result.sha256 is not None
    assert result.xxhash is None
    assert result.phash is None


def test_hash_single_file_handles_permission_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("hello")

    def _raise_permission(_: Path, chunk_size: int = hasher_module.CHUNK_SIZE) -> str:
        raise PermissionError

    monkeypatch.setattr(hasher_module, "compute_sha256", _raise_permission)
    result = _hash_single_file((file_path, False, False))

    assert result.error == "Permission denied"


def test_hash_single_file_handles_file_not_found(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("hello")

    def _raise_missing(_: Path, chunk_size: int = hasher_module.CHUNK_SIZE) -> str:
        raise FileNotFoundError

    monkeypatch.setattr(hasher_module, "compute_sha256", _raise_missing)
    result = _hash_single_file((file_path, False, False))

    assert result.error == "File not found"


def test_hash_single_file_handles_unexpected_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("hello")

    def _raise_runtime(_: Path, chunk_size: int = hasher_module.CHUNK_SIZE) -> str:
        raise RuntimeError("boom")

    monkeypatch.setattr(hasher_module, "compute_sha256", _raise_runtime)
    result = _hash_single_file((file_path, False, False))

    assert result.error == "boom"


def test_parallel_hasher_hash_files_handles_success_and_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ok_path = tmp_path / "ok.bin"
    warned_path = tmp_path / "warn.bin"
    crash_path = tmp_path / "crash.bin"

    files = [
        FileMetadata(path=ok_path, size=1, mtime=1.0),
        FileMetadata(path=warned_path, size=1, mtime=2.0),
        FileMetadata(path=crash_path, size=1, mtime=3.0),
    ]

    class _FakeFuture:
        def __init__(self, result: HashResult | None = None, exc: Exception | None = None) -> None:
            self._result = result
            self._exc = exc

        def result(self) -> HashResult:
            if self._exc:
                raise self._exc
            assert self._result is not None
            return self._result

    class _FakeExecutor:
        def __init__(self, max_workers: int | None = None) -> None:
            self.max_workers = max_workers

        def __enter__(self) -> "_FakeExecutor":
            return self

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            return False

        def submit(self, fn: Any, args: tuple[Path, bool, bool]) -> _FakeFuture:
            del fn
            path = args[0]
            if path == ok_path:
                return _FakeFuture(
                    result=HashResult(path=path, sha256="sha-ok", xxhash="xx-ok", phash="ph-ok")
                )
            if path == warned_path:
                return _FakeFuture(result=HashResult(path=path, error="hash warning"))
            return _FakeFuture(exc=RuntimeError("future exploded"))

    def _fake_as_completed(futures: dict[_FakeFuture, Path]) -> list[_FakeFuture]:
        return list(futures.keys())

    monkeypatch.setattr(hasher_module, "ProcessPoolExecutor", _FakeExecutor)
    monkeypatch.setattr(hasher_module, "as_completed", _fake_as_completed)

    progress_events: list[tuple[int, int]] = []
    hasher = ParallelHasher(max_workers=2, use_xxhash=True, compute_perceptual=True)
    result_files = hasher.hash_files(
        files,
        progress_callback=lambda processed, total: progress_events.append((processed, total)),
    )

    assert result_files is files
    assert files[0].sha256 == "sha-ok"
    assert files[0].xxhash == "xx-ok"
    assert files[0].phash == "ph-ok"
    assert files[1].sha256 is None
    assert files[2].sha256 is None
    assert hasher.stats == {"processed": 2, "errors": 2}
    assert progress_events == [(1, 3), (2, 3)]


def test_parallel_hasher_empty_input_returns_early() -> None:
    hasher = ParallelHasher(max_workers=1)
    assert hasher.hash_files([]) == []
    assert hasher.stats == {"processed": 0, "errors": 0}


def test_hash_batch_delegates_to_hash_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    file_meta = FileMetadata(path=tmp_path / "a.bin", size=1, mtime=1.0)

    def callback(*_: Any) -> None:
        return None

    called: dict[str, Any] = {}

    def _fake_hash_files(
        self: ParallelHasher,
        batch: list[FileMetadata],
        progress_callback: Any = None,
    ) -> list[FileMetadata]:
        called["batch"] = batch
        called["progress_callback"] = progress_callback
        return batch

    monkeypatch.setattr(ParallelHasher, "hash_files", _fake_hash_files)

    hasher = ParallelHasher(max_workers=1)
    result = hasher.hash_batch([file_meta], progress_callback=callback)

    assert result == [file_meta]
    assert called["batch"] == [file_meta]
    assert called["progress_callback"] is callback


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


def test_hamming_distance_rejects_mismatched_lengths() -> None:
    with pytest.raises(ValueError):
        hamming_distance("ffff", "fff")


def test_hashes_are_similar() -> None:
    assert hashes_are_similar("ffff", "ffff", threshold=0) is True
    assert hashes_are_similar("ffff", "fff0", threshold=4) is True


def test_hashes_are_similar_handles_invalid_hash_values() -> None:
    assert hashes_are_similar("zzzz", "ffff", threshold=10) is False
    assert hashes_are_similar("ffff", cast("str", None), threshold=10) is False
