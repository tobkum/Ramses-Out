"""Preview scanner for finding preview files in Ramses project structure."""

import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from .models import PreviewItem

# Add shared Ramses API library path (project root)
lib_path = Path(__file__).parent.parent.parent / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

from ramses.constants import FolderNames


class PreviewScanner:
    """Scans Ramses project for preview files."""

    def __init__(self, project_root: str):
        """Initialize scanner with project root path."""
        self.project_root = Path(project_root)
        self.shots_folder = self.project_root / FolderNames.shots

    def scan_project(self) -> List[PreviewItem]:
        """Scan project for all preview files.

        Returns:
            List of PreviewItem objects found in the project.
        """
        previews = []

        if not self.shots_folder.exists():
            return previews

        try:
            # Scan all shot folders
            for shot_folder in self.shots_folder.iterdir():
                if not shot_folder.is_dir():
                    continue

                try:
                    # Scan all step folders within shot
                    for step_folder in shot_folder.iterdir():
                        if not step_folder.is_dir():
                            continue

                        # Check for _preview folder
                        preview_folder = step_folder / "_preview"
                        if not preview_folder.exists():
                            continue

                        # Scan for preview files in _preview folder
                        for preview_file in preview_folder.iterdir():
                            if preview_file.is_file() and preview_file.suffix.lower() in ['.mp4', '.mov']:
                                preview = self._parse_preview_file(
                                    preview_file, shot_folder, step_folder
                                )
                                if preview:
                                    previews.append(preview)
                except (PermissionError, OSError):
                    # Skip shots we can't read
                    continue
        except (PermissionError, OSError):
            # Inaccessible shots root
            pass

        return previews

    def _parse_preview_file(
        self, file_path: Path, shot_folder: Path, step_folder: Path
    ) -> Optional[PreviewItem]:
        """Parse a preview file and create PreviewItem.

        Uses the folder context supplied by ``scan_project`` (which already
        walked the correct depth) as the primary source of IDs.  Falls back
        to filename-based parsing only when the folder name doesn't contain
        the expected ``_S_`` Ramses delimiter.

        Using ``rsplit('_S_', 1)`` (split at the *last* occurrence) handles
        project names that themselves contain ``_S_`` without producing extra
        parts.

        Args:
            file_path: Path to the preview file.
            shot_folder: The shot directory (parent of the step directory).
            step_folder: The step directory (parent of ``_preview``).

        Returns:
            PreviewItem or None if parsing fails.
        """
        project_id = None
        shot_id = None
        step_id = None

        try:
            # Primary: derive IDs from the known folder structure.
            # rsplit at last '_S_' so project names containing '_S_' are handled.
            shot_parts = shot_folder.name.rsplit('_S_', 1)
            if len(shot_parts) == 2:
                project_id = shot_parts[0]
                shot_id = shot_parts[1]

                # Step ID: strip the shot-folder prefix from the step-folder name.
                prefix = shot_folder.name + '_'
                step_id = (
                    step_folder.name[len(prefix):]
                    if step_folder.name.startswith(prefix)
                    else step_folder.name
                )

            # Fallback: filename-based parsing when folder names lack '_S_'.
            if not all((project_id, shot_id, step_id)):
                parts = file_path.stem.rsplit('_S_', 1)
                if len(parts) != 2:
                    return None
                project_id = parts[0]
                rest = parts[1].split('_', 1)
                if len(rest) != 2:
                    return None
                shot_id, step_id = rest

            # Get file info
            stat = file_path.stat()
            file_size = stat.st_size
            date_modified = datetime.fromtimestamp(stat.st_mtime)

            # Check for marker file and compare with preview modification time
            marker_path, sent_date, status = self._check_marker(file_path.parent, date_modified)

            return PreviewItem(
                shot_id=shot_id,
                sequence_id="",  # Resolved later
                step_id=step_id,
                project_id=project_id,
                file_path=str(file_path),
                file_size=file_size,
                date_modified=date_modified,
                format=file_path.suffix[1:].lower(),
                status=status,
                marker_path=marker_path,
                sent_date=sent_date
            )
        except (OSError, ValueError):
            return None

    def _check_marker(self, preview_folder: Path, preview_modified: datetime) -> tuple[Optional[str], Optional[str], str]:
        """Check for review marker file in preview folder.

        Args:
            preview_folder: Path to _preview folder
            preview_modified: Modification time of the preview file

        Returns:
            Tuple of (marker_path, sent_date, status)
        """
        marker_files = []
        try:
            # Look for .review_sent_YYYY-MM-DD[_HHMMSS].txt files and find the most recent one
            for marker_file in preview_folder.glob('.review_sent_*.txt'):
                # Flexible regex: matches YYYY-MM-DD and optionally any suffix before .txt
                match = re.search(r'\.review_sent_(\d{4}-\d{2}-\d{2}).*\.txt', marker_file.name)
                if match:
                    sent_date = match.group(1)
                    try:
                        marker_stat = marker_file.stat()
                        marker_modified = datetime.fromtimestamp(marker_stat.st_mtime)
                        marker_files.append((marker_file, sent_date, marker_modified))
                    except OSError:
                        continue
        except (PermissionError, OSError):
            pass

        if not marker_files:
            return None, None, "Ready"

        # Sort by modification time and get the most recent marker
        marker_files.sort(key=lambda x: x[2], reverse=True)
        most_recent_marker, sent_date, marker_modified = marker_files[0]

        # Compare marker timestamp with preview modification time
        if preview_modified > marker_modified:
            return str(most_recent_marker), sent_date, "Ready (Updated)"

        return str(most_recent_marker), sent_date, f"Sent {sent_date}"

    @staticmethod
    def filter_by_date(items: List[PreviewItem], date_range: str) -> List[PreviewItem]:
        """Filter preview items by date range.

        Args:
            items: List of preview items
            date_range: Date range filter ("Today", "This Week", "This Month", "All")

        Returns:
            Filtered list of preview items
        """
        if date_range == "All":
            return items

        now = datetime.now()
        today = now.date()
        filtered = []

        for item in items:
            item_date = item.date_modified.date()
            if date_range == "Today":
                if item_date == today:
                    filtered.append(item)
            elif date_range == "This Week":
                # Current week (Monday to Sunday)
                start_of_week = today - timedelta(days=today.weekday())
                if item_date >= start_of_week:
                    filtered.append(item)
            elif date_range == "This Month":
                if item_date.month == today.month and item_date.year == today.year:
                    filtered.append(item)

        return filtered

    @staticmethod
    def filter_by_sequence(items: List[PreviewItem], sequence: str) -> List[PreviewItem]:
        """Filter preview items by sequence.

        Args:
            items: List of preview items
            sequence: Sequence ID or "All"

        Returns:
            Filtered list of preview items
        """
        if sequence == "All":
            return items

        return [item for item in items if item.sequence_id == sequence]

    @staticmethod
    def filter_by_step(items: List[PreviewItem], step: str) -> List[PreviewItem]:
        """Filter preview items by step.

        Args:
            items: List of preview items
            step: Step ID or "All"

        Returns:
            Filtered list of preview items
        """
        if step == "All":
            return items

        return [item for item in items if item.step_id == step]
