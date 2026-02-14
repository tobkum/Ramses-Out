"""Upload tracking system using marker files and history log."""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Add shared Ramses API library path (project root)
import sys
lib_path = Path(__file__).parent.parent.parent / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

from .models import PreviewItem


class UploadTracker:
    """Manages upload markers and history log."""

    def __init__(self):
        """Initialize tracker."""
        self.history_log = self._get_history_log_path()

    def _get_history_log_path(self) -> Path:
        """Get path to upload history log.

        Returns:
            Path to .ramses/upload_history.log
        """
        home = Path.home()
        ramses_dir = home / ".ramses"
        ramses_dir.mkdir(exist_ok=True)
        return ramses_dir / "upload_history.log"

    def _get_username(self) -> str:
        """Get the current Ramses username, fallback to system username."""
        try:
            from ramses import Ramses
            ram = Ramses.instance()
            user = ram.user()
            if user:
                return user.name()
        except Exception:
            pass

        import getpass
        return getpass.getuser()

    def create_marker(self, preview_item: PreviewItem, package_name: str, notes: str = "") -> bool:
        """Create marker file for uploaded preview.

        Args:
            preview_item: The preview that was uploaded
            package_name: Name of the review package
            notes: Optional notes about the upload

        Returns:
            True if marker created successfully
        """
        preview_path = Path(preview_item.file_path)
        preview_folder = preview_path.parent

        # Create marker filename with current date and timestamp to prevent overwrites
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H%M%S")
        marker_filename = f".review_sent_{date_str}_{time_str}.txt"
        marker_path = preview_folder / marker_filename

        # Get username
        username = self._get_username()

        # Write marker file
        try:
            with open(marker_path, "w", encoding="utf-8") as f:
                f.write(f"Uploaded: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Destination: fTrack Review\n")
                f.write(f"User: {username}\n")
                f.write(f"Package: {package_name}\n")
                if notes:
                    f.write(f"Notes: {notes}\n")

            return True
        except Exception:
            return False

    def read_marker(self, marker_path: str) -> Optional[dict]:
        """Read marker file and extract metadata.

        Args:
            marker_path: Path to marker file

        Returns:
            Dictionary with marker metadata or None
        """
        try:
            with open(marker_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            metadata = {}
            for line in lines:
                if ": " in line:
                    key, value = line.strip().split(": ", 1)
                    metadata[key.lower()] = value

            return metadata
        except Exception:
            return None

    def append_to_log(self, preview_items: List[PreviewItem], package_name: str) -> bool:
        """Append upload entry to history log.

        Args:
            preview_items: List of previews that were uploaded
            package_name: Name of the review package

        Returns:
            True if appended successfully
        """
        username = self._get_username()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Sanitize fields to prevent log corruption
        safe_package = package_name.replace("|", "-")

        try:
            with open(self.history_log, "a", encoding="utf-8") as f:
                for item in preview_items:
                    # Format: timestamp|Review|shot_id|step|fTrack|username|package_name
                    entry = f"{timestamp}|Review|{item.shot_id}|{item.step_id}|fTrack|{username}|{safe_package}\n"
                    f.write(entry)

            return True
        except Exception:
            return False

    def get_history(self, shot_id: str) -> List[dict]:
        """Get upload history for a specific shot.

        Args:
            shot_id: Shot ID to query

        Returns:
            List of upload history entries
        """
        if not self.history_log.exists():
            return []

        history = []
        try:
            with open(self.history_log, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split("|")
                    if len(parts) >= 7 and parts[2] == shot_id:
                        history.append({
                            "timestamp": parts[0],
                            "type": parts[1],
                            "shot_id": parts[2],
                            "step": parts[3],
                            "destination": parts[4],
                            "user": parts[5],
                            "package": parts[6]
                        })

            return history
        except Exception:
            return []

    def mark_as_sent(self, preview_items: List[PreviewItem], package_name: str, notes: str = "") -> bool:
        """Mark multiple previews as sent.

        Args:
            preview_items: List of previews to mark
            package_name: Name of the review package
            notes: Optional notes

        Returns:
            True if all markers created successfully
        """
        # Sanitize inputs
        safe_package = package_name.replace("|", "-")
        safe_notes = notes.replace("|", "-")

        success = True
        for item in preview_items:
            if not self.create_marker(item, safe_package, safe_notes):
                success = False

        # Append to history log
        if success:
            self.append_to_log(preview_items, safe_package)

        return success
