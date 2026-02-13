"""Data models for Ramses Out."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class PreviewItem:
    """Represents a preview file ready for review."""

    shot_id: str
    sequence_id: str
    step_id: str
    project_id: str
    file_path: str
    file_size: int
    date_modified: datetime
    format: str  # mp4, mov, etc.
    status: str  # "Ready", "Sent YYYY-MM-DD", "Outdated"
    marker_path: Optional[str] = None
    sent_date: Optional[str] = None  # YYYY-MM-DD format

    @property
    def display_name(self) -> str:
        """Get display name for the preview."""
        return f"{self.project_id}_S_{self.shot_id}_{self.step_id}.{self.format}"

    @property
    def size_mb(self) -> float:
        """Get file size in megabytes."""
        return self.file_size / (1024 * 1024)

    @property
    def is_ready(self) -> bool:
        """Check if preview is ready for review (not sent yet)."""
        return self.status.startswith("Ready")
