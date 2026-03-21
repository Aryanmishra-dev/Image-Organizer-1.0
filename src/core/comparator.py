"""Duplicate detection and grouping logic with multiple strategies."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

from .hasher import hashes_are_similar
from .scanner import FileMetadata

logger = logging.getLogger(__name__)


def similarity_percent_to_hamming_threshold(percent: int) -> int:
    """Map user-facing similarity percent (0-100) to Hamming threshold (0-64)."""
    clamped = max(0, min(100, percent))
    return max(0, min(64, round((100 - clamped) / 100 * 64)))


class DuplicateType(Enum):
    """Types of duplicate detection."""

    EXACT = "exact"  # Identical SHA-256 hash
    PERCEPTUAL = "perceptual"  # Similar perceptual hash
    SIZE_ONLY = "size_only"  # Same size (needs verification)


@dataclass
class DuplicateGroup:
    """A group of duplicate files."""

    group_id: int
    duplicate_type: DuplicateType
    key: str  # Hash or identifier
    members: list[FileMetadata] = field(default_factory=list)

    @property
    def total_size(self) -> int:
        """Total size of all files in group."""
        return sum(m.size for m in self.members)

    @property
    def wasted_size(self) -> int:
        """Size that could be recovered (all but one copy)."""
        if len(self.members) <= 1:
            return 0
        return self.total_size - min(m.size for m in self.members)

    @property
    def count(self) -> int:
        return len(self.members)

    def get_original(self, strategy: str = "oldest") -> FileMetadata | None:
        """
        Determine which file to keep based on strategy.

        Strategies:
        - oldest: Keep file with earliest modification time
        - newest: Keep file with latest modification time
        - largest: Keep largest file (highest quality)
        - smallest: Keep smallest file (most compressed)
        - shortest_path: Keep file with shortest path (likely more organized)
        """
        if not self.members:
            return None

        if strategy == "oldest":
            return min(self.members, key=lambda m: m.mtime)
        elif strategy == "newest":
            return max(self.members, key=lambda m: m.mtime)
        elif strategy == "largest":
            return max(self.members, key=lambda m: m.size)
        elif strategy == "smallest":
            return min(self.members, key=lambda m: m.size)
        elif strategy == "shortest_path":
            return min(self.members, key=lambda m: len(str(m.path)))
        else:
            return self.members[0]

    def get_duplicates(self, strategy: str = "oldest") -> list[FileMetadata]:
        """Get all files except the one to keep."""
        original = self.get_original(strategy)
        if not original:
            return []
        return [m for m in self.members if m.path != original.path]


@dataclass
class ComparisonResult:
    """Result of duplicate comparison."""

    exact_groups: list[DuplicateGroup] = field(default_factory=list)
    perceptual_groups: list[DuplicateGroup] = field(default_factory=list)
    total_duplicates: int = 0
    total_wasted_bytes: int = 0
    scan_stats: dict = field(default_factory=dict)


class DuplicateComparator:
    """
    Groups files by hash or similarity.
    Supports multiple detection strategies.
    """

    def __init__(
        self,
        similarity_threshold: int = 10,
        min_group_size: int = 2,
    ) -> None:
        """
        Initialize comparator.

        Args:
            similarity_threshold: Max Hamming distance for perceptual matches (0-64)
            min_group_size: Minimum files to form a duplicate group
        """
        self.similarity_threshold = similarity_threshold
        self.min_group_size = min_group_size
        self._group_counter = 0

    def _next_group_id(self) -> int:
        self._group_counter += 1
        return self._group_counter

    def find_all_duplicates(
        self,
        files: list[FileMetadata],
        include_perceptual: bool = True,
        progress_callback: Callable[[str], None] | None = None,
    ) -> ComparisonResult:
        """
        Find all duplicates using multiple strategies.

        Args:
            files: List of files with hashes computed
            include_perceptual: Also find perceptually similar images
            progress_callback: Optional status callback

        Returns:
            ComparisonResult with all duplicate groups
        """
        result = ComparisonResult()

        # Stage 1: Exact duplicates (same SHA-256)
        if progress_callback:
            progress_callback("Finding exact duplicates...")
        result.exact_groups = self.group_by_exact_hash(files)

        # Stage 2: Perceptual duplicates (similar images)
        if include_perceptual:
            if progress_callback:
                progress_callback("Finding similar images...")
            # Only check files with phash that aren't already exact duplicates
            exact_paths: set[str] = set()
            for group in result.exact_groups:
                for member in group.members:
                    exact_paths.add(str(member.path))

            remaining = [f for f in files if str(f.path) not in exact_paths and f.phash]
            result.perceptual_groups = self.group_by_perceptual_hash(remaining)

        # Calculate totals
        for group in result.exact_groups + result.perceptual_groups:
            result.total_duplicates += group.count - 1  # -1 for original
            result.total_wasted_bytes += group.wasted_size

        return result

    def group_by_exact_hash(self, files: list[FileMetadata]) -> list[DuplicateGroup]:
        """
        Group files by exact SHA-256 hash.
        This is the primary duplicate detection method.
        """
        buckets: dict[str, list[FileMetadata]] = defaultdict(list)

        for meta in files:
            if meta.sha256:
                buckets[meta.sha256].append(meta)

        groups = []
        for hash_key, members in buckets.items():
            if len(members) >= self.min_group_size:
                groups.append(
                    DuplicateGroup(
                        group_id=self._next_group_id(),
                        duplicate_type=DuplicateType.EXACT,
                        key=hash_key,
                        members=members,
                    )
                )

        # Sort by wasted size (largest first)
        groups.sort(key=lambda g: g.wasted_size, reverse=True)
        return groups

    def group_by_perceptual_hash(self, files: list[FileMetadata]) -> list[DuplicateGroup]:
        """
        Group files by perceptual hash similarity.
        Uses clustering to handle transitive similarity.
        """
        if not files:
            return []

        # Filter to files with phash
        hashable = [f for f in files if f.phash]
        if len(hashable) < 2:
            return []

        # Build similarity graph using Union-Find for clustering
        parent: dict[str, str] = {}

        def find(x: str) -> str:
            if x not in parent:
                parent[x] = x
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x: str, y: str) -> None:
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        # Compare all pairs (O(n²) but necessary for perceptual matching)
        path_to_meta = {str(m.path): m for m in hashable}
        paths = list(path_to_meta.keys())

        for i, path1 in enumerate(paths):
            meta1 = path_to_meta[path1]
            for path2 in paths[i + 1 :]:
                meta2 = path_to_meta[path2]
                if (
                    meta1.phash
                    and meta2.phash
                    and hashes_are_similar(meta1.phash, meta2.phash, self.similarity_threshold)
                ):
                    union(path1, path2)

        # Group by cluster root
        clusters: dict[str, list[FileMetadata]] = defaultdict(list)
        for path, meta in path_to_meta.items():
            root = find(path)
            clusters[root].append(meta)

        # Create groups
        groups = []
        for root, members in clusters.items():
            if len(members) >= self.min_group_size:
                groups.append(
                    DuplicateGroup(
                        group_id=self._next_group_id(),
                        duplicate_type=DuplicateType.PERCEPTUAL,
                        key=f"phash_cluster_{root[:16]}",
                        members=members,
                    )
                )

        groups.sort(key=lambda g: g.wasted_size, reverse=True)
        return groups

    def group_by_size(self, files: list[FileMetadata]) -> list[DuplicateGroup]:
        """
        Group files by size only (fast preliminary grouping).
        Use this to identify candidates before computing hashes.
        """
        buckets: dict[int, list[FileMetadata]] = defaultdict(list)

        for meta in files:
            buckets[meta.size].append(meta)

        groups = []
        for size, members in buckets.items():
            if len(members) >= self.min_group_size:
                groups.append(
                    DuplicateGroup(
                        group_id=self._next_group_id(),
                        duplicate_type=DuplicateType.SIZE_ONLY,
                        key=f"size_{size}",
                        members=members,
                    )
                )

        return groups

    def filter_by_priority_paths(
        self,
        groups: list[DuplicateGroup],
        priority_paths: list[str],
    ) -> list[DuplicateGroup]:
        """
        Reorder group members to prioritize keeping files in certain directories.
        Files in priority paths are moved to the front of the members list.

        Args:
            groups: Duplicate groups
            priority_paths: List of path prefixes to prioritize
        """
        for group in groups:

            def priority_key(meta: FileMetadata) -> int:
                path_str = str(meta.path)
                for i, prefix in enumerate(priority_paths):
                    if path_str.startswith(prefix):
                        return i
                return len(priority_paths)

            group.members.sort(key=priority_key)

        return groups


def format_duplicate_report(result: ComparisonResult) -> str:
    """Format comparison result as human-readable string."""
    lines = [
        "=" * 60,
        "DUPLICATE SCAN RESULTS",
        "=" * 60,
        "",
        f"Exact duplicate groups: {len(result.exact_groups)}",
        f"Perceptual similar groups: {len(result.perceptual_groups)}",
        f"Total duplicate files: {result.total_duplicates}",
        f"Potential space savings: {result.total_wasted_bytes:,} bytes "
        f"({result.total_wasted_bytes / (1024*1024):.1f} MB)",
        "",
    ]

    if result.exact_groups:
        lines.append("-" * 40)
        lines.append("EXACT DUPLICATES (Top 10)")
        lines.append("-" * 40)
        for group in result.exact_groups[:10]:
            lines.append(
                f"\nGroup {group.group_id} ({group.count} files, "
                f"{group.wasted_size:,} bytes wasted):"
            )
            for member in group.members[:5]:
                lines.append(f"  • {member.path}")
            if group.count > 5:
                lines.append(f"  ... and {group.count - 5} more")

    if result.perceptual_groups:
        lines.append("")
        lines.append("-" * 40)
        lines.append("SIMILAR IMAGES (Top 10)")
        lines.append("-" * 40)
        for group in result.perceptual_groups[:10]:
            lines.append(f"\nGroup {group.group_id} ({group.count} files):")
            for member in group.members[:5]:
                lines.append(f"  • {member.path}")
            if group.count > 5:
                lines.append(f"  ... and {group.count - 5} more")

    return "\n".join(lines)
