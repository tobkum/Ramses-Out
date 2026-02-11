"""Tests for upload tracking functionality."""

import os
import sys
import unittest
import tempfile
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ramses_review.tracker import UploadTracker
from ramses_review.models import PreviewItem


class TestUploadTracker(unittest.TestCase):
    """Test upload tracking and marker files."""

    def setUp(self):
        """Create temp directories and tracker."""
        self.temp_dir = tempfile.mkdtemp()
        self.preview_folder = Path(self.temp_dir) / "_preview"
        self.preview_folder.mkdir(parents=True)

        self.preview_file = self.preview_folder / "TEST_S_SH010_COMP.mp4"
        self.preview_file.write_text("fake video")

        # Create tracker with custom history log path
        self.tracker = UploadTracker()
        self.tracker.history_log = Path(self.temp_dir) / "test_history.log"

    def create_preview_item(self, shot_id="SH010", step_id="COMP"):
        """Create a test PreviewItem."""
        return PreviewItem(
            shot_id=shot_id,
            sequence_id="SEQ01",
            step_id=step_id,
            project_id="TEST",
            file_path=str(self.preview_file),
            file_size=1024,
            date_modified=datetime.now(),
            format="mp4",
            status="Ready",
        )

    def test_create_marker(self):
        """Test creating a marker file."""
        item = self.create_preview_item()
        package_name = "TEST_20260211"

        success = self.tracker.create_marker(item, package_name, "Test notes")

        self.assertTrue(success)

        # Check marker file exists
        markers = list(self.preview_folder.glob(".review_sent_*.txt"))
        self.assertEqual(len(markers), 1)

        # Check marker content
        marker_content = markers[0].read_text()
        self.assertIn("Uploaded:", marker_content)
        self.assertIn("fTrack Review", marker_content)
        self.assertIn(package_name, marker_content)
        self.assertIn("Test notes", marker_content)

    def test_read_marker(self):
        """Test reading marker metadata."""
        item = self.create_preview_item()
        self.tracker.create_marker(item, "TEST_20260211", "Test notes")

        markers = list(self.preview_folder.glob(".review_sent_*.txt"))
        marker_path = str(markers[0])

        metadata = self.tracker.read_marker(marker_path)

        self.assertIsNotNone(metadata)
        self.assertIn("uploaded", metadata)
        self.assertIn("destination", metadata)
        self.assertIn("package", metadata)
        self.assertEqual(metadata["package"], "TEST_20260211")

    def test_append_to_log(self):
        """Test appending to history log."""
        items = [
            self.create_preview_item("SH010", "COMP"),
            self.create_preview_item("SH020", "ANIM"),
        ]

        success = self.tracker.append_to_log(items, "TEST_20260211")

        self.assertTrue(success)
        self.assertTrue(self.tracker.history_log.exists())

        # Read log and verify entries
        log_content = self.tracker.history_log.read_text()
        self.assertIn("SH010", log_content)
        self.assertIn("SH020", log_content)
        self.assertIn("COMP", log_content)
        self.assertIn("ANIM", log_content)
        self.assertIn("TEST_20260211", log_content)

    def test_get_history(self):
        """Test retrieving upload history for a shot."""
        items = [self.create_preview_item("SH010", "COMP")]

        self.tracker.append_to_log(items, "TEST_20260211_V1")
        self.tracker.append_to_log(items, "TEST_20260211_V2")

        history = self.tracker.get_history("SH010")

        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["shot_id"], "SH010")
        self.assertEqual(history[0]["step"], "COMP")

    def test_mark_as_sent_multiple(self):
        """Test marking multiple previews as sent."""
        items = [
            self.create_preview_item("SH010", "COMP"),
            self.create_preview_item("SH020", "ANIM"),
        ]

        # Create separate preview folders for each
        for item in items:
            folder = Path(self.temp_dir) / f"_preview_{item.shot_id}"
            folder.mkdir()
            preview_file = folder / f"TEST_S_{item.shot_id}_{item.step_id}.mp4"
            preview_file.write_text("fake video")
            item.file_path = str(preview_file)

        success = self.tracker.mark_as_sent(items, "TEST_20260211", "Batch upload")

        self.assertTrue(success)

        # Check markers created for both
        for item in items:
            folder = Path(item.file_path).parent
            markers = list(folder.glob(".review_sent_*.txt"))
            self.assertEqual(len(markers), 1)

        # Check history log
        self.assertTrue(self.tracker.history_log.exists())
        log_content = self.tracker.history_log.read_text()
        self.assertIn("SH010", log_content)
        self.assertIn("SH020", log_content)

    def test_marker_with_no_notes(self):
        """Test creating marker without notes."""
        item = self.create_preview_item()
        success = self.tracker.create_marker(item, "TEST_20260211", "")

        self.assertTrue(success)

        markers = list(self.preview_folder.glob(".review_sent_*.txt"))
        marker_content = markers[0].read_text()

        # Should not have "Notes:" line if notes are empty
        self.assertNotIn("Notes:", marker_content)

    def test_history_log_permissions_error(self):
        """Test handling of permissions error on history log."""
        # Make history log read-only
        self.tracker.history_log.write_text("initial")
        os.chmod(self.tracker.history_log, 0o444)

        items = [self.create_preview_item()]

        try:
            success = self.tracker.append_to_log(items, "TEST_20260211")
            # Should fail gracefully
            self.assertFalse(success)
        finally:
            # Restore permissions for cleanup
            os.chmod(self.tracker.history_log, 0o644)

    def tearDown(self):
        """Clean up temp directories."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
