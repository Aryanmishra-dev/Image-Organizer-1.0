"""High-performance hashing with streaming, multiprocessing, and perceptual hashing."""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

try:
    import xxhash

    HAS_XXHASH = True
except ImportError:
    HAS_XXHASH = False

try:
    import imagehash
    from PIL import Image

    HAS_IMAGEHASH = True
except ImportError:
    HAS_IMAGEHASH = False

from duplicate_image_detector.io.scanner import FileMetadata

logger = logging.getLogger(__name__)

# Chunk size for streaming file reads (1MB)
CHUNK_SIZE = 1024 * 1024


@dataclass
class HashResult:
    """Result of hashing a single file."""

    path: Path
    sha256: str | None = None
    xxhash: str | None = None
    phash: str | None = None
    error: str | None = None


def compute_sha256(path: Path, chunk_size: int = CHUNK_SIZE) -> str:
    """
    Stream file and return hex SHA-256.
    Memory-efficient: only loads chunk_size bytes at a time.
    """
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compute_xxhash(path: Path, chunk_size: int = CHUNK_SIZE) -> str | None:
    """
    Faster non-cryptographic hash using xxHash.
    ~3x faster than SHA-256 for large files.
    """
    if not HAS_XXHASH:
        return None
    h = xxhash.xxh3_128()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            h.update(chunk)
    return cast("str", h.hexdigest())


def compute_phash(path: Path, hash_size: int = 16) -> str | None:
    """
    Compute perceptual hash for images.
    Similar images will have similar hashes (small Hamming distance).

    Args:
        path: Path to image file
        hash_size: Size of hash (default 16 for 256-bit hash)

    Returns:
        Hex string of perceptual hash, or None if not an image
    """
    if not HAS_IMAGEHASH:
        return None
    try:
        with Image.open(path) as img:
            target: Any = img
            # Convert to RGB if necessary (handles RGBA, P mode, etc.)
            if img.mode not in ("RGB", "L"):
                target = img.convert("RGB")
            return str(imagehash.phash(target, hash_size=hash_size))
    except Exception as e:
        logger.debug(f"Could not compute phash for {path}: {e}")
        return None


def compute_dhash(path: Path, hash_size: int = 16) -> str | None:
    """
    Compute difference hash for images.
    More sensitive to structural changes than pHash.
    """
    if not HAS_IMAGEHASH:
        return None
    try:
        with Image.open(path) as img:
            target: Any = img
            if img.mode not in ("RGB", "L"):
                target = img.convert("RGB")
            return str(imagehash.dhash(target, hash_size=hash_size))
    except Exception as e:
        logger.debug(f"Could not compute dhash for {path}: {e}")
        return None


def compute_average_hash(path: Path, hash_size: int = 16) -> str | None:
    """Compute average hash (aHash) for images."""
    if not HAS_IMAGEHASH:
        return None
    try:
        with Image.open(path) as img:
            target: Any = img
            if img.mode not in ("RGB", "L"):
                target = img.convert("RGB")
            return str(imagehash.average_hash(target, hash_size=hash_size))
    except Exception as e:
        logger.debug(f"Could not compute ahash for {path}: {e}")
        return None


def _hash_single_file(args: tuple[Path, bool, bool]) -> HashResult:
    """
    Hash a single file (designed to run in a separate process).

    Args:
        args: Tuple of (path, compute_perceptual, use_xxhash)
    """
    path, compute_perceptual, use_xxhash = args
    result = HashResult(path=path)

    try:
        # Always compute SHA-256 for exact matching
        result.sha256 = compute_sha256(path)

        # Optionally compute xxhash for faster preliminary checks
        if use_xxhash:
            result.xxhash = compute_xxhash(path)

        # Compute perceptual hash for images
        if compute_perceptual:
            suffix = path.suffix.lower()
            image_extensions = {
                ".jpg",
                ".jpeg",
                ".png",
                ".gif",
                ".bmp",
                ".tiff",
                ".tif",
                ".webp",
                ".heic",
                ".heif",
            }
            if suffix in image_extensions:
                result.phash = compute_phash(path)

    except PermissionError:
        result.error = "Permission denied"
    except FileNotFoundError:
        result.error = "File not found"
    except Exception as e:
        result.error = str(e)

    return result


class ParallelHasher:
    """
    High-performance parallel file hasher using multiprocessing.
    Optimized for Apple Silicon with configurable worker count.
    """

    def __init__(
        self,
        max_workers: int | None = None,
        use_xxhash: bool = True,
        compute_perceptual: bool = False,
    ) -> None:
        """
        Initialize parallel hasher.

        Args:
            max_workers: Number of worker processes (default: CPU count)
            use_xxhash: Also compute xxHash for faster preliminary matching
            compute_perceptual: Compute perceptual hashes for images
        """
        import os

        self.max_workers = max_workers or min(os.cpu_count() or 4, 10)
        self.use_xxhash = use_xxhash
        self.compute_perceptual = compute_perceptual
        self._processed = 0
        self._errors = 0

    @property
    def stats(self) -> dict[str, int]:
        return {"processed": self._processed, "errors": self._errors}

    def hash_files(
        self,
        files: list[FileMetadata],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[FileMetadata]:
        """
        Hash files in parallel and update FileMetadata objects.

        Args:
            files: List of FileMetadata to hash
            progress_callback: Optional callback(processed, total)

        Returns:
            Updated list of FileMetadata with hash values populated
        """
        self._processed = 0
        self._errors = 0
        total = len(files)

        if total == 0:
            return files

        # Prepare arguments for parallel processing
        args_list = [(meta.path, self.compute_perceptual, self.use_xxhash) for meta in files]

        # Create path -> metadata lookup
        path_to_meta = {str(meta.path): meta for meta in files}

        # Process in parallel
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(_hash_single_file, args): args[0] for args in args_list}

            for future in as_completed(futures):
                try:
                    result = future.result()
                    meta = path_to_meta.get(str(result.path))

                    if meta and not result.error:
                        meta.sha256 = result.sha256
                        meta.xxhash = result.xxhash
                        meta.phash = result.phash
                    elif result.error:
                        self._errors += 1
                        logger.warning(f"Error hashing {result.path}: {result.error}")

                    self._processed += 1

                    if progress_callback:
                        progress_callback(self._processed, total)

                except Exception as e:
                    self._errors += 1
                    logger.error(f"Future error: {e}")

        return files

    def hash_batch(
        self,
        batch: list[FileMetadata],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[FileMetadata]:
        """Alias for hash_files for API consistency."""
        return self.hash_files(batch, progress_callback)


def hamming_distance(hash1: str, hash2: str) -> int:
    """
    Calculate Hamming distance between two hex hash strings.
    Used to compare perceptual hashes - lower = more similar.
    """
    if len(hash1) != len(hash2):
        raise ValueError("Hashes must be same length")

    # Convert hex to binary and count differing bits
    n1 = int(hash1, 16)
    n2 = int(hash2, 16)
    xor = n1 ^ n2
    return bin(xor).count("1")


def hashes_are_similar(hash1: str, hash2: str, threshold: int = 10) -> bool:
    """
    Check if two perceptual hashes are similar (within threshold).

    For 256-bit hashes (hash_size=16):
    - 0-5: Nearly identical images
    - 6-10: Very similar (different compression, minor edits)
    - 11-20: Somewhat similar
    - 20+: Different images
    """
    try:
        return hamming_distance(hash1, hash2) <= threshold
    except (ValueError, TypeError):
        return False
