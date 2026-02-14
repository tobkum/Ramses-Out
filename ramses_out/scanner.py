"""Preview scanner for finding preview files in Ramses project structure."""

import os
import re
import sys
from datetime import datetime
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

        # Scan all shot folders
        for shot_folder in self.shots_folder.iterdir():
            if not shot_folder.is_dir():
                continue

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
                        preview = self._parse_preview_file(preview_file)
                        if preview:
                            previews.append(preview)

        return previews

    def _parse_preview_file(self, file_path: Path) -> Optional[PreviewItem]:
        """Parse a preview file and create PreviewItem.

        Tries to extract project/shot/step from the filename first
        (expected format: {PROJECT}_S_{SHOT}_{STEP}.{ext}).
        Falls back to extracting from the folder structure when the
        filename doesn't match.

        Args:
            file_path: Path to the preview file

        Returns:
            PreviewItem or None if parsing fails
        """
        project_id = None
        shot_id = None
        step_id = None

        # Try filename-based parsing: {PROJECT}_S_{SHOT}_{STEP}.{ext}
        filename = file_path.stem
        parts = filename.split('_S_')

        if len(parts) == 2:
            rest_parts = parts[1].split('_', 1)
            if len(rest_parts) == 2:
                project_id = parts[0]
                shot_id = rest_parts[0]
                step_id = rest_parts[1]

        # Fallback: extract from folder structure
        # _preview -> step_folder -> shot_folder -> 05-SHOTS
        if not all((project_id, shot_id, step_id)):
            step_folder = file_path.parent.parent   # e.g. Testprojec_S_120_Comp
            shot_folder = step_folder.parent         # e.g. Testprojec_S_120

            shot_parts = shot_folder.name.split('_S_')
            if len(shot_parts) != 2:
                return None

            project_id = shot_parts[0]
            shot_id = shot_parts[1]

            # Step ID: strip the shot folder prefix from step folder name
            step_name = step_folder.name
            prefix = shot_folder.name + '_'
            if step_name.startswith(prefix):
                step_id = step_name[len(prefix):]
            else:
                step_id = step_name

        # Sequence is resolved later via the Ramses API (see gui._resolve_sequences)
        sequence_id = ""

        # Get file info
        stat = file_path.stat()
        file_size = stat.st_size
        date_modified = datetime.fromtimestamp(stat.st_mtime)

        # Check for marker file and compare with preview modification time
        marker_path, sent_date, status = self._check_marker(file_path.parent, date_modified)

        return PreviewItem(
            shot_id=shot_id,
            sequence_id=sequence_id,
            step_id=step_id,
            project_id=project_id,
            file_path=str(file_path),
            file_size=file_size,
            date_modified=date_modified,
            format=file_path.suffix[1:].lower(),  # Remove leading dot
            status=status,
            marker_path=marker_path,
            sent_date=sent_date
        )

    def _check_marker(self, preview_folder: Path, preview_modified: datetime) -> tuple[Optional[str], Optional[str], str]:
        """Check for review marker file in preview folder.

        Args:
            preview_folder: Path to _preview folder
            preview_modified: Modification time of the preview file

        Returns:
            Tuple of (marker_path, sent_date, status)
        """
        # Look for .review_sent_YYYY-MM-DD[_HHMMSS].txt files and find the most recent one
        marker_files = []
        for marker_file in preview_folder.glob('.review_sent_*.txt'):
            # Flexible regex: matches YYYY-MM-DD and optionally any suffix before .txt
            match = re.search(r'\.review_sent_(\d{4}-\d{2}-\d{2}).*\.txt', marker_file.name)
            if match:
                sent_date = match.group(1)
                marker_stat = marker_file.stat()
                marker_modified = datetime.fromtimestamp(marker_stat.st_mtime)
                marker_files.append((marker_file, sent_date, marker_modified))

        if not marker_files:
            return None, None, "Ready"

        # Sort by modification time and get the most recent marker
        marker_files.sort(key=lambda x: x[2], reverse=True)
        most_recent_marker, sent_date, marker_modified = marker_files[0]

        # Compare marker timestamp with preview modification time
        if preview_modified > marker_modified:
            return str(most_recent_marker), sent_date, "Ready (Updated)"

        return str(most_recent_marker), sent_date, f"Sent {sent_date}"

    def filter_by_date(self, items: List[PreviewItem], date_range: str) -> List[PreviewItem]:
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

    def filter_by_sequence(self, items: List[PreviewItem], sequence: str) -> List[PreviewItem]:
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

    def filter_by_step(self, items: List[PreviewItem], step: str) -> List[PreviewItem]:
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
