from pathlib import Path

from duplicate_image_detector.io.scanner import FileScanner, ScanConfig, format_size


def test_scanner_batches_tmp(tmp_path: Path) -> None:
    for idx in range(3):
        (tmp_path / f"file{idx}.txt").write_text("x")
    config = ScanConfig(batch_size=2)
    scanner = FileScanner(config)
    batches = list(scanner.scan([tmp_path]))
    assert len(batches) == 2
    assert sum(len(b) for b in batches) == 3


def test_scanner_filters_by_extension(tmp_path: Path) -> None:
    (tmp_path / "image.jpg").write_text("img")
    (tmp_path / "doc.txt").write_text("txt")
    config = ScanConfig(file_extensions={".jpg"})
    scanner = FileScanner(config)
    files = [f for batch in scanner.scan([tmp_path]) for f in batch]
    assert len(files) == 1
    assert files[0].path.suffix == ".jpg"


def test_format_size() -> None:
    assert format_size(500) == "500.0 B"
    assert format_size(1024) == "1.0 KB"
    assert format_size(1024 * 1024) == "1.0 MB"


def test_scanner_protected_paths_use_ancestry_not_prefix(tmp_path: Path) -> None:
    root = tmp_path / "root"
    protected = root / "protected"
    sibling = root / "protected_docs"
    protected.mkdir(parents=True)
    sibling.mkdir(parents=True)

    blocked_file = protected / "blocked.txt"
    allowed_file = sibling / "allowed.txt"
    blocked_file.write_text("blocked")
    allowed_file.write_text("allowed")

    config = ScanConfig(
        protected_paths=[str(protected)],
        ignore_hidden=False,
    )
    scanner = FileScanner(config)
    files = [f for batch in scanner.scan([root]) for f in batch]
    scanned_paths = {str(f.path) for f in files}

    assert str(blocked_file) not in scanned_paths
    assert str(allowed_file) in scanned_paths
