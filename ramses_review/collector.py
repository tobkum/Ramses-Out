"""File collection and shot list generation."""

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
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> bool:
        """Collect preview files to destination folder.

        Args:
            items: List of preview items to collect
            dest: Destination folder path
            progress_callback: Optional callback(current, total, filename)

        Returns:
            True if collection succeeded
        """
        dest_path = Path(dest)
        dest_path.mkdir(parents=True, exist_ok=True)

        total = len(items)
        for idx, item in enumerate(items, 1):
            source = Path(item.file_path)

            if not source.exists():
                continue

            # Copy file to destination
            dest_file = dest_path / source.name

            if progress_callback:
                progress_callback(idx, total, source.name)

            try:
                shutil.copy2(source, dest_file)
            except Exception:
                return False

        return True

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

        # Sort sequences
        for seq in sorted(by_sequence.keys()):
            seq_items = by_sequence[seq]
            lines.append(f"# {seq}")
            lines.append("")

            for item in sorted(seq_items, key=lambda x: x.shot_id):
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
