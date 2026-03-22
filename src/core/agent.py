"""
Rule-based smart agent for duplicate analysis and recommendations.
Prioritizes quality, time, and location signals without external APIs.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

logger = logging.getLogger(__name__)


IMAGE_FORMAT_SCORES = {
    ".png": 10,
    ".jpg": 5,
    ".jpeg": 5,
    ".gif": 0,
    ".webp": 7,
    ".tif": 7,
    ".tiff": 7,
    ".heic": 8,
}

UNORGANIZED_KEYWORDS = {"downloads", "desktop", "tmp", "temp", "cache"}
ORGANIZED_HINTS = {"photos", "pictures", "images", "library", "archive"}
IMAGE_EXTENSIONS = set(IMAGE_FORMAT_SCORES.keys())


@dataclass
class FileScore:
    path: Path
    size_bytes: int
    created: float
    modified: float
    width: int
    height: int
    extension: str
    format_label: str
    has_exif: bool
    organized: bool
    random_name: bool
    protected: bool
    location_score: float
    resolution_score: float
    size_score: float
    time_score: float
    format_score: float
    metadata_bonus: float
    total_score: float


class DuplicateAgent:
    """Rule-based agent that scores duplicates and suggests actions."""

    def __init__(self, protected_folders: Sequence[str] | None = None) -> None:
        self.protected_folders = [Path(p).expanduser().resolve() for p in (protected_folders or [])]

    def analyze_duplicates(
        self,
        duplicate_groups: list[dict[str, Any]],
        user_preferences: dict[str, Any] | None = None,
        status_callback: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        if not user_preferences:
            user_preferences = {
                "keep_strategy": "newest",
                "similarity_threshold": 90,
                "preserve_folders": [],
            }

        strategy = user_preferences.get("keep_strategy", "newest")
        protected = self._protected_paths(user_preferences.get("preserve_folders", []))
        self.protected_folders = protected

        recommendations: list[dict[str, Any]] = []
        total_space = 0
        valid_groups = 0

        for idx, group in enumerate(duplicate_groups):
            if status_callback:
                status_callback(f"Analyzing group {idx + 1}/{len(duplicate_groups)}...")

            group_id = self._extract_group_id(group, idx)
            file_paths = self._extract_paths(group)
            scores = self._score_group(file_paths, strategy, protected)

            if len(scores) < 2:
                continue

            valid_groups += 1
            winner, loser_scores = self._pick_winner(scores)
            confidence = self._confidence_level(winner, loser_scores)
            remove_files = [fs.path for fs in loser_scores if not fs.protected]

            space_saved = sum(fs.size_bytes for fs in loser_scores if not fs.protected)
            total_space += space_saved

            reason = self._reason_text(winner, loser_scores, strategy, confidence, remove_files)

            recommendations.append(
                {
                    "group_id": group_id,
                    "keep_file": str(winner.path),
                    "remove_files": [str(p) for p in remove_files],
                    "reason": reason,
                    "confidence": confidence,
                    "space_saved_bytes": space_saved,
                }
            )

        space_mb = round(total_space / (1024 * 1024), 2)
        summary = (
            f"Found {valid_groups} groups, can save {space_mb:.2f} MB using {strategy} strategy"
        )

        return {
            "summary": summary,
            "total_groups": valid_groups,
            "space_to_save_mb": space_mb,
            "space_to_save_bytes": total_space,
            "recommendations": recommendations,
            "method": "rule_based",
        }

    def execute_recommendations(
        self,
        recommendations: list[dict[str, Any]],
        backup_dir: Path | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        import shutil

        backup_dir = backup_dir or Path.home() / ".dupclean_backup"

        if not dry_run:
            backup_dir.mkdir(parents=True, exist_ok=True)

        results: dict[str, Any] = {
            "dry_run": dry_run,
            "files_processed": 0,
            "files_removed": 0,
            "space_freed": 0,
            "errors": [],
            "actions": [],
        }

        for rec in recommendations:
            for file_path in rec.get("remove_files", []):
                path = Path(file_path)
                results["files_processed"] += 1

                if not path.exists():
                    results["errors"].append(f"File not found: {file_path}")
                    continue

                if self._is_protected(path):
                    results["actions"].append({"action": "skipped_protected", "file": str(path)})
                    continue

                try:
                    size = path.stat().st_size

                    if dry_run:
                        results["actions"].append(
                            {"action": "would_remove", "file": str(path), "size": size}
                        )
                    else:
                        dest = backup_dir / path.name
                        counter = 1
                        while dest.exists():
                            dest = backup_dir / f"{path.stem}_{counter}{path.suffix}"
                            counter += 1

                        shutil.move(str(path), str(dest))
                        results["actions"].append(
                            {
                                "action": "moved",
                                "from": str(path),
                                "to": str(dest),
                                "size": size,
                            }
                        )

                    results["files_removed"] += 1
                    results["space_freed"] += size

                except Exception as exc:  # pragma: no cover - safety net
                    results["errors"].append(f"Error processing {file_path}: {exc}")

        return results

    def _score_group(
        self, file_paths: list[str], strategy: str, protected: list[Path]
    ) -> list[FileScore]:
        scores: list[FileScore] = []

        for path_str in file_paths:
            try:
                path = Path(path_str).expanduser()
                if not path.exists():
                    continue

                stat = path.stat()
                width, height, img_format, has_exif = self._image_info(path)

                size_bytes = stat.st_size
                created = getattr(stat, "st_birthtime", stat.st_ctime)
                modified = stat.st_mtime
                extension = path.suffix.lower()
                organized = self._looks_organized(path)
                random_name = self._looks_random_name(path.stem)
                is_protected = self._is_protected(path, protected)
                location_score = self._location_score(path, organized, random_name, is_protected)

                scores.append(
                    FileScore(
                        path=path,
                        size_bytes=size_bytes,
                        created=created,
                        modified=modified,
                        width=width,
                        height=height,
                        extension=extension,
                        format_label=img_format,
                        has_exif=has_exif,
                        organized=organized,
                        random_name=random_name,
                        protected=is_protected,
                        location_score=location_score,
                        resolution_score=0.0,
                        size_score=0.0,
                        time_score=0.0,
                        format_score=0.0,
                        metadata_bonus=0.0,
                        total_score=0.0,
                    )
                )
            except Exception as exc:
                logger.debug(f"Skipping {path_str}: {exc}")
                continue

        if len(scores) < 2:
            return scores

        max_resolution = max((fs.width * fs.height for fs in scores), default=0)
        max_size = max((fs.size_bytes for fs in scores), default=1)
        min_time = min((fs.created for fs in scores), default=0)
        max_time = max((fs.created for fs in scores), default=0)

        for fs in scores:
            fs.resolution_score = self._resolution_score(fs.width, fs.height, max_resolution)
            fs.size_score = self._size_score(fs.size_bytes, max_size)
            fs.time_score = self._time_score(fs.created, min_time, max_time, strategy)
            fs.format_score = IMAGE_FORMAT_SCORES.get(fs.extension, 5 if fs.extension else 0)
            fs.metadata_bonus = 5.0 if fs.has_exif else 0.0
            raw_total = (
                fs.resolution_score
                + fs.size_score
                + fs.time_score
                + fs.location_score
                + fs.format_score
                + fs.metadata_bonus
            )
            fs.total_score = max(0.0, min(100.0, raw_total))

        return scores

    def _pick_winner(self, scores: list[FileScore]) -> tuple[FileScore, list[FileScore]]:
        sorted_scores = sorted(scores, key=lambda s: (s.total_score, s.created), reverse=True)
        winner = sorted_scores[0]
        losers = sorted_scores[1:]
        return winner, losers

    def _confidence_level(self, winner: FileScore, losers: list[FileScore]) -> str:
        if not losers:
            return "high"

        second_best = losers[0].total_score
        diff = winner.total_score - second_best

        if diff > 30:
            return "high"
        if diff >= 10:
            return "medium"
        return "low"

    def _reason_text(
        self,
        winner: FileScore,
        losers: list[FileScore],
        strategy: str,
        confidence: str,
        remove_files: list[Path],
    ) -> str:
        parts: list[str] = []

        if winner.width and winner.height:
            parts.append(f"Highest resolution ({winner.width}x{winner.height})")

        max_loser_size = max((fs.size_bytes for fs in losers), default=0)
        if winner.size_bytes >= max_loser_size > 0:
            saved_mb = (winner.size_bytes - max_loser_size) / (1024 * 1024)
            parts.append(f"Largest file (+{saved_mb:.1f} MB vs next)")

        if (
            winner.format_score >= max((fs.format_score for fs in losers), default=0)
            and winner.extension
        ):
            parts.append(f"Preferred format ({winner.extension})")

        if strategy in {"newest", "oldest"}:
            parts.append(f"{strategy.title()} creation date")

        if winner.organized:
            parts.append("Organized folder structure")
        if winner.protected:
            parts.append("Protected directory prioritized")
        if winner.random_name:
            parts.append("Filename seems random; kept due to other signals")

        if confidence == "low":
            parts.append("Quality difference is small; review before deleting")
        elif not remove_files:
            parts.append("No removals suggested because alternatives are protected")

        return ", ".join(parts) if parts else "Keeping best-scored file"

    def _resolution_score(self, width: int, height: int, max_resolution: int) -> float:
        if not width or not height or not max_resolution:
            return 0.0
        return min(40.0, (width * height / max_resolution) * 40.0)

    def _size_score(self, size_bytes: int, max_size: int) -> float:
        if not size_bytes or not max_size:
            return 0.0
        return min(20.0, (size_bytes / max_size) * 20.0)

    def _time_score(self, created: float, min_time: float, max_time: float, strategy: str) -> float:
        if not created or max_time == min_time:
            return 10.0

        span = max_time - min_time
        if span <= 0:
            return 10.0

        if strategy == "newest":
            return min(20.0, ((created - min_time) / span) * 20.0)
        if strategy == "oldest":
            return min(20.0, ((max_time - created) / span) * 20.0)

        return 10.0

    def _location_score(
        self, path: Path, organized: bool, random_name: bool, is_protected: bool
    ) -> float:
        score = 0.0
        path_lower = str(path).lower()

        if organized:
            score += 15.0
        if any(keyword in path_lower for keyword in UNORGANIZED_KEYWORDS):
            score -= 10.0
        if random_name:
            score -= 10.0
        if is_protected:
            score += 20.0

        return max(-10.0, min(20.0, score))

    def _image_info(self, path: Path) -> tuple[int, int, str, bool]:
        width = height = 0
        img_format = ""
        has_exif = False

        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            return width, height, img_format, has_exif

        try:
            with Image.open(path) as img:
                width, height = img.width, img.height
                img_format = (img.format or "").lower()
                exif_data: Any = getattr(img, "getexif", lambda: {})()
                has_exif = bool(exif_data)
        except Exception as exc:
            logger.debug(f"Could not read image metadata for {path}: {exc}")

        return width, height, img_format, has_exif

    def _looks_random_name(self, stem: str) -> bool:
        normalized = stem.lower()
        if re.fullmatch(r"[a-f0-9]{8,}", normalized):
            return True
        if re.fullmatch(r"img_\d{4,}", normalized):
            return True
        if re.fullmatch(r"dsc\d{4,}", normalized):
            return True
        return len(normalized) > 20 and bool(re.fullmatch(r"[a-z0-9_\-]+", normalized))

    def _looks_organized(self, path: Path) -> bool:
        parts = [p.lower() for p in path.parts]
        has_year = any(
            part.isdigit() and len(part) == 4 and part.startswith(("19", "20")) for part in parts
        )
        has_hint = any(part in ORGANIZED_HINTS for part in parts)
        return has_year or has_hint or len(parts) >= 4

    def _protected_paths(self, preserved: Sequence[str]) -> list[Path]:
        merged = list(self.protected_folders)
        for p in preserved:
            try:
                merged.append(Path(p).expanduser().resolve())
            except (OSError, RuntimeError, ValueError):
                continue
        return merged

    def _is_protected(self, path: Path, custom: list[Path] | None = None) -> bool:
        candidates = custom if custom is not None else self.protected_folders
        try:
            resolved = path.resolve()
        except (OSError, RuntimeError, ValueError):
            resolved = path

        for protected in candidates:
            try:
                protected_path = protected.resolve()
            except (OSError, RuntimeError, ValueError):
                protected_path = protected

            if resolved == protected_path or protected_path in resolved.parents:
                return True

        return False

    def _extract_group_id(self, group: Any, default: int) -> int:
        if isinstance(group, dict):
            return int(group.get("group_id", default))
        return int(getattr(group, "group_id", default))

    def _extract_paths(self, group: Any) -> list[str]:
        paths: list[str] = []
        if isinstance(group, dict):
            candidates = group.get("files") or group.get("members") or []
        elif hasattr(group, "members"):
            candidates = getattr(group, "members", [])
        else:
            candidates = []

        for item in candidates:
            if isinstance(item, dict):
                value = item.get("path")
            elif hasattr(item, "path"):
                value = item.path
            else:
                value = item

            if value:
                paths.append(str(value))

        return paths
