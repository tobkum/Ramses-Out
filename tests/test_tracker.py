"""Tests for upload tracking functionality."""

import os
import sys
import unittest
import tempfile
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ramses_out.tracker import UploadTracker
from ramses_out.models import PreviewItem


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
        self.assertIn("Local Collection", marker_content)
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
        """Test appending to history log with project_id."""
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
        self.assertIn("|TEST\n", log_content)  # Should have project_id at the end

    def test_get_history(self):
        """Test retrieving upload history for a shot filtered by project."""
        items = [self.create_preview_item("SH010", "COMP")]

        self.tracker.append_to_log(items, "TEST_20260211_V1")
        
        # Add entry for same shot but different project
        other_item = self.create_preview_item("SH010", "COMP")
        other_item.project_id = "OTHER"
        self.tracker.append_to_log([other_item], "OTHER_PACKAGE")

        # Get history for SH010 in project TEST
        history_test = self.tracker.get_history("SH010", "TEST")
        self.assertEqual(len(history_test), 1)
        self.assertEqual(history_test[0]["project_id"], "TEST")

        # Get history for SH010 in project OTHER
        history_other = self.tracker.get_history("SH010", "OTHER")
        self.assertEqual(len(history_other), 1)
        self.assertEqual(history_other[0]["project_id"], "OTHER")

        # Legacy behavior: no project_id filters nothing
        history_all = self.tracker.get_history("SH010")
        self.assertEqual(len(history_all), 2)

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

    def test_marker_contains_file_field(self):
        """Markers must name the exact preview file they belong to."""
        item = self.create_preview_item()
        self.assertTrue(self.tracker.create_marker(item, "PKG", ""))

        markers = list(self.preview_folder.glob(".review_sent_*.txt"))
        self.assertEqual(len(markers), 1)
        content = markers[0].read_text()
        self.assertIn(f"File: {self.preview_file.name}", content)

    def test_markers_for_sibling_files_do_not_collide(self):
        """Two previews in one folder marked in the same second must produce
        two distinct markers (previously the same-second filename collided,
        and X.mp4 / X.mov share a stem)."""
        sibling = self.preview_folder / "TEST_S_SH010_COMP.mov"
        sibling.write_text("fake video")

        item_a = self.create_preview_item()
        item_b = self.create_preview_item()
        item_b.file_path = str(sibling)
        item_b.format = "mov"

        self.assertTrue(self.tracker.mark_as_sent([item_a, item_b], "PKG"))

        markers = list(self.preview_folder.glob(".review_sent_*.txt"))
        self.assertEqual(len(markers), 2)
        targets = {self.tracker.read_marker(str(m)).get("file") for m in markers}
        self.assertEqual(targets, {Path(item_a.file_path).name, sibling.name})

    def test_set_project_root_relocates_history_log(self):
        """set_project_root points the log at <project>/_deliveries/ and the
        directory is created lazily on the first write."""
        project_root = Path(self.temp_dir) / "PROJ"
        project_root.mkdir()

        self.tracker.set_project_root(str(project_root))
        expected = project_root / "_deliveries" / "upload_history.log"
        self.assertEqual(self.tracker.history_log, expected)
        self.assertFalse(expected.parent.exists())  # lazy — no dir until write

        self.assertTrue(self.tracker.append_to_log([self.create_preview_item()], "PKG"))
        self.assertTrue(expected.exists())
        self.assertIn("SH010", expected.read_text())

        # History queries follow the new log
        self.assertEqual(len(self.tracker.get_history("SH010")), 1)

    def test_set_project_root_empty_is_noop(self):
        """An empty project root must not break the fallback log path."""
        before = self.tracker.history_log
        self.tracker.set_project_root("")
        self.assertEqual(self.tracker.history_log, before)

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
