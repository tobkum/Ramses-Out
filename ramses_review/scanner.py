"""Preview scanner for finding preview files in Ramses project structure."""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .models import PreviewItem


class PreviewScanner:
    """Scans Ramses project for preview files."""

    def __init__(self, project_root: str):
        """Initialize scanner with project root path."""
        self.project_root = Path(project_root)
        self.shots_folder = self.project_root / "05-SHOTS"

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

        Args:
            file_path: Path to the preview file

        Returns:
            PreviewItem or None if parsing fails
        """
        # Expected format: {PROJECT}_S_{SHOT}_{STEP}.{ext}
        filename = file_path.stem
        parts = filename.split('_S_')

        if len(parts) != 2:
            return None

        project_id = parts[0]
        rest = parts[1]

        # Split shot and step
        rest_parts = rest.split('_', 1)
        if len(rest_parts) != 2:
            return None

        shot_id = rest_parts[0]
        step_id = rest_parts[1]

        # Extract sequence from shot folder name
        shot_folder = file_path.parent.parent
        sequence_id = self._extract_sequence(shot_folder.name)

        # Get file info
        stat = file_path.stat()
        file_size = stat.st_size
        date_modified = datetime.fromtimestamp(stat.st_mtime)

        # Check for marker file
        marker_path, sent_date, status = self._check_marker(file_path.parent)

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

    def _extract_sequence(self, shot_folder_name: str) -> str:
        """Extract sequence ID from shot folder name.

        Args:
            shot_folder_name: Name of the shot folder

        Returns:
            Sequence ID or empty string
        """
        # Try to extract sequence from folder name
        # Common patterns: SEQ01, SQ01, 01, etc.
        match = re.search(r'(SEQ|SQ)?(\d+)', shot_folder_name, re.IGNORECASE)
        if match:
            return f"SEQ{match.group(2)}" if match.group(2) else ""
        return ""

    def _check_marker(self, preview_folder: Path) -> tuple[Optional[str], Optional[str], str]:
        """Check for review marker file in preview folder.

        Args:
            preview_folder: Path to _preview folder

        Returns:
            Tuple of (marker_path, sent_date, status)
        """
        # Look for .review_sent_*.txt files
        for marker_file in preview_folder.glob('.review_sent_*.txt'):
            # Extract date from filename: .review_sent_2026-02-11.txt
            match = re.search(r'\.review_sent_(\d{4}-\d{2}-\d{2})\.txt', marker_file.name)
            if match:
                sent_date = match.group(1)
                return str(marker_file), sent_date, f"Sent {sent_date}"

        return None, None, "Ready"

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
        filtered = []

        for item in items:
            if date_range == "Today":
                if item.date_modified.date() == now.date():
                    filtered.append(item)
            elif date_range == "This Week":
                days_ago = (now - item.date_modified).days
                if days_ago <= 7:
                    filtered.append(item)
            elif date_range == "This Month":
                if item.date_modified.month == now.month and item.date_modified.year == now.year:
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
