"""File collection and shot list generation."""

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Callable, Optional

from .models import PreviewItem


class PreviewCollector:
    """Handles collection of preview files to a destination folder."""

    def collect_files(
        self,
        items: List[PreviewItem],
        dest: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> bool:
        """Collect preview files to destination folder.

        Args:
            items: List of preview items to collect
            dest: Destination folder path
            progress_callback: Optional callback(current, total, filename)
            cancel_check: Optional callback that returns True if cancellation requested

        Returns:
            True if collection succeeded, False if cancelled or failed
        """
        dest_path = Path(dest)
        dest_path.mkdir(parents=True, exist_ok=True)

        total = len(items)
        copied_count = 0
        failed_files = []

        for idx, item in enumerate(items, 1):
            # Check for cancellation
            if cancel_check and cancel_check():
                return False

            source = Path(item.file_path)

            if not source.exists():
                failed_files.append((source.name, "File not found"))
                continue

            # Copy file to destination
            dest_file = dest_path / source.name

            if progress_callback:
                progress_callback(idx, total, source.name)

            try:
                shutil.copy2(source, dest_file)
                copied_count += 1
            except Exception as e:
                failed_files.append((source.name, str(e)))

        # Success if we copied at least some files and had no failures
        return copied_count > 0 and len(failed_files) == 0

    def _natural_sort_key(self, s: str):
        """Key for natural alphanumeric sorting (e.g., SH1, SH2, SH10)."""
        return [int(text) if text.isdigit() else text.lower()
                for text in re.split('([0-9]+)', s)]

    def generate_shot_list(self, items: List[PreviewItem], project_name: str) -> str:
        """Generate shot list manifest text.

        Args:
            items: List of preview items
            project_name: Project name

        Returns:
            Shot list text content
        """
        lines = []
        lines.append(f"Review Package - {project_name}")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("")

        # Group by sequence
        by_sequence = {}
        for item in items:
            seq = item.sequence_id or "UNKNOWN"
            if seq not in by_sequence:
                by_sequence[seq] = []
            by_sequence[seq].append(item)

        # Sort sequences naturally
        for seq in sorted(by_sequence.keys(), key=self._natural_sort_key):
            seq_items = by_sequence[seq]
            lines.append(f"# {seq}")
            lines.append("")

            # Sort items by shot_id naturally
            for item in sorted(seq_items, key=lambda x: self._natural_sort_key(x.shot_id)):
                # Format: SH010 - COMP - 1920x1080 @ 24fps (23.4 MB)
                line = f"{item.shot_id} - {item.step_id} - {item.format.upper()} ({item.size_mb:.1f} MB)"
                lines.append(line)

            lines.append("")

        lines.append("─" * 60)
        lines.append(f"Total: {len(items)} shots")

        return "\n".join(lines)

    def save_shot_list(self, items: List[PreviewItem], dest: str, project_name: str) -> bool:
        """Save shot list to file.

        Args:
            items: List of preview items
            dest: Destination folder
            project_name: Project name

        Returns:
            True if saved successfully
        """
        dest_path = Path(dest)
        shot_list_path = dest_path / "shot_list.txt"

        content = self.generate_shot_list(items, project_name)

        try:
            with open(shot_list_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception:
            return False
