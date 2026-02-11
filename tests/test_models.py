"""Tests for data models."""

import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ramses_review.models import PreviewItem


class TestPreviewItem(unittest.TestCase):
    """Test PreviewItem data model."""

    def create_item(self, status="Ready", **kwargs):
        """Create a test PreviewItem with defaults."""
        defaults = {
            "shot_id": "SH010",
            "sequence_id": "SEQ01",
            "step_id": "COMP",
            "project_id": "TEST",
            "file_path": "/path/to/TEST_S_SH010_COMP.mp4",
            "file_size": 1024 * 1024,  # 1 MB
            "date_modified": datetime.now(),
            "format": "mp4",
            "status": status,
        }
        defaults.update(kwargs)
        return PreviewItem(**defaults)

    def test_display_name(self):
        """Test display name generation."""
        item = self.create_item()
        expected = "TEST_S_SH010_COMP.mp4"
        self.assertEqual(item.display_name, expected)

    def test_size_mb(self):
        """Test file size conversion to MB."""
        item = self.create_item(file_size=2 * 1024 * 1024)  # 2 MB
        self.assertAlmostEqual(item.size_mb, 2.0, places=1)

        item_half = self.create_item(file_size=512 * 1024)  # 0.5 MB
        self.assertAlmostEqual(item_half.size_mb, 0.5, places=1)

    def test_is_ready_for_ready_status(self):
        """Test is_ready returns True for Ready status."""
        item = self.create_item(status="Ready")
        self.assertTrue(item.is_ready)

    def test_is_ready_for_updated_status(self):
        """Test is_ready returns True for Ready (Updated) status."""
        item = self.create_item(status="Ready (Updated)")
        self.assertTrue(item.is_ready)

    def test_is_ready_for_sent_status(self):
        """Test is_ready returns False for Sent status."""
        item = self.create_item(status="Sent 2026-02-11")
        self.assertFalse(item.is_ready)

    def test_marker_metadata(self):
        """Test marker path and sent date metadata."""
        item = self.create_item(
            status="Sent 2026-02-11",
            marker_path="/path/to/_preview/.review_sent_2026-02-11.txt",
            sent_date="2026-02-11",
        )

        self.assertEqual(item.status, "Sent 2026-02-11")
        self.assertEqual(item.marker_path, "/path/to/_preview/.review_sent_2026-02-11.txt")
        self.assertEqual(item.sent_date, "2026-02-11")
        self.assertFalse(item.is_ready)

    def test_different_formats(self):
        """Test different video formats."""
        for fmt in ["mp4", "mov", "avi"]:
            item = self.create_item(format=fmt)
            self.assertEqual(item.format, fmt)
            self.assertIn(fmt, item.display_name)

    def test_sequence_id_optional(self):
        """Test sequence_id can be empty."""
        item = self.create_item(sequence_id="")
        self.assertEqual(item.sequence_id, "")

    def test_date_modified_stores_datetime(self):
        """Test date_modified stores datetime object."""
        now = datetime.now()
        item = self.create_item(date_modified=now)
        self.assertEqual(item.date_modified, now)
        self.assertIsInstance(item.date_modified, datetime)


if __name__ == "__main__":
    unittest.main()
