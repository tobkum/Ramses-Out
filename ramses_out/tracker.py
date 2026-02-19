"""Upload tracking system using marker files and history log."""

import contextlib
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add shared Ramses API library path (project root)
lib_path = Path(__file__).parent.parent.parent / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

from .models import PreviewItem


@contextlib.contextmanager
def _log_lock(log_path: Path, timeout: float = 10.0):
    """Cross-process advisory lock for the history log file.

    Uses ``O_CREAT | O_EXCL`` (atomic on POSIX and Windows NTFS) so two
    concurrent Ramses-Out instances writing to a shared network log cannot
    interleave their entries.  Stale locks older than ``timeout`` seconds
    are forcibly removed.
    """
    lock_path = log_path.with_suffix(".lock")
    deadline = time.monotonic() + timeout
    acquired = False
    while not acquired:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            acquired = True
        except FileExistsError:
            if time.monotonic() >= deadline:
                try:
                    os.remove(str(lock_path))
                except OSError:
                    pass
                # One final attempt; propagate if it still fails.
                fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                acquired = True
            else:
                time.sleep(0.05)
    try:
        yield
    finally:
        try:
            os.remove(str(lock_path))
        except OSError:
            pass


class UploadTracker:
    """Manages upload markers and history log."""

    def __init__(self):
        """Initialize tracker."""
        self.history_log = self._get_history_log_path()
        # In-memory cache of the history log keyed by shot_id.
        # None means the cache is stale and must be rebuilt on next access.
        self._history_cache: Optional[Dict[str, List[dict]]] = None

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
                f.write(f"Destination: Local Collection\n")
                f.write(f"User: {username}\n")
                f.write(f"Package: {package_name}\n")
                if notes:
                    f.write(f"Notes: {notes}\n")

            return True
        except Exception as e:
            print(f"Error creating marker: {e}")
            return False

    def read_marker(self, marker_path: str) -> Optional[dict]:
        """Read marker file and extract metadata.

        Handles multi-line values (e.g. notes that span several lines): any
        line that does not contain ``": "`` is treated as a continuation of
        the previous key's value.

        Args:
            marker_path: Path to marker file

        Returns:
            Dictionary with marker metadata or None
        """
        try:
            with open(marker_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            metadata: dict = {}
            last_key: Optional[str] = None
            for line in lines:
                stripped = line.rstrip("\n")
                if ": " in stripped:
                    key, value = stripped.split(": ", 1)
                    last_key = key.strip().lower()
                    metadata[last_key] = value.strip()
                elif last_key is not None and stripped.strip():
                    # Continuation line — append to the previous key's value.
                    metadata[last_key] = metadata[last_key] + "\n" + stripped.strip()

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
        username = self._get_username().replace("|", "-")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Sanitize fields to prevent log corruption
        safe_package = package_name.replace("|", "-")

        try:
            with _log_lock(self.history_log):
                with open(self.history_log, "a", encoding="utf-8") as f:
                    for item in preview_items:
                        safe_shot = item.shot_id.replace("|", "-")
                        safe_step = item.step_id.replace("|", "-")
                        # Format: timestamp|Review|shot_id|step|Local|username|package_name
                        entry = f"{timestamp}|Review|{safe_shot}|{safe_step}|Local|{username}|{safe_package}\n"
                        f.write(entry)
            self._history_cache = None  # invalidate cache after write
            return True
        except Exception as e:
            print(f"Error appending to history log: {e}")
            return False

    def _ensure_history_cache(self) -> None:
        """Build the in-memory history cache from disk if it is stale."""
        if self._history_cache is not None:
            return
        cache: Dict[str, List[dict]] = {}
        if self.history_log.exists():
            try:
                with open(self.history_log, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split("|")
                        if len(parts) >= 7:
                            entry = {
                                "timestamp": parts[0],
                                "type": parts[1],
                                "shot_id": parts[2],
                                "step": parts[3],
                                "destination": parts[4],
                                "user": parts[5],
                                "package": parts[6],
                            }
                            cache.setdefault(parts[2], []).append(entry)
            except Exception:
                pass
        self._history_cache = cache

    def get_history(self, shot_id: str) -> List[dict]:
        """Get upload history for a specific shot.

        Uses an in-memory cache so repeated queries do not re-read the entire
        log file.  The cache is invalidated automatically after each write via
        ``append_to_log``.

        Args:
            shot_id: Shot ID to query

        Returns:
            List of upload history entries
        """
        self._ensure_history_cache()
        return list(self._history_cache.get(shot_id, []))  # type: ignore[union-attr]

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
