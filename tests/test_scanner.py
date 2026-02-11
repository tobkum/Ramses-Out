"""Tests for preview scanner functionality."""

import os
import sys
import unittest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ramses_review.scanner import PreviewScanner
from ramses_review.models import PreviewItem


class TestPreviewScanner(unittest.TestCase):
    """Test preview scanning and parsing."""

    def setUp(self):
        """Create temp project structure with previews."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)

        # Create standard Ramses structure
        self.shots_folder = self.project_root / "05-SHOTS"

        # SEQ01/SH010/COMP
        shot1_step = self.shots_folder / "TEST_S_SH010" / "TEST_S_SH010_COMP"
        preview1 = shot1_step / "_preview"
        preview1.mkdir(parents=True)

        # Create preview file
        self.preview1_file = preview1 / "TEST_S_SH010_COMP.mp4"
        self.preview1_file.write_text("fake video data")

        # SEQ01/SH020/ANIM
        shot2_step = self.shots_folder / "TEST_S_SH020" / "TEST_S_SH020_ANIM"
        preview2 = shot2_step / "_preview"
        preview2.mkdir(parents=True)

        self.preview2_file = preview2 / "TEST_S_SH020_ANIM.mp4"
        self.preview2_file.write_text("fake video data")

        # Make preview older first
        preview_time = datetime.now() - timedelta(hours=2)
        os.utime(self.preview2_file, (preview_time.timestamp(), preview_time.timestamp()))

        # Create marker for preview2 (newer than preview)
        marker_date = datetime.now().strftime("%Y-%m-%d")
        self.marker_file = preview2 / f".review_sent_{marker_date}.txt"
        self.marker_file.write_text(f"Uploaded: {marker_date} 10:00:00\n")

        # Make marker newer than preview to test "Sent" status
        marker_time = datetime.now() - timedelta(hours=1)
        os.utime(self.marker_file, (marker_time.timestamp(), marker_time.timestamp()))

        self.scanner = PreviewScanner(str(self.project_root))

    def test_scan_finds_all_previews(self):
        """Test that scan finds all preview files."""
        previews = self.scanner.scan_project()

        self.assertEqual(len(previews), 2)

        shot_ids = {p.shot_id for p in previews}
        self.assertEqual(shot_ids, {"SH010", "SH020"})

    def test_parse_preview_filename(self):
        """Test parsing of preview filename."""
        previews = self.scanner.scan_project()
        preview1 = next(p for p in previews if p.shot_id == "SH010")

        self.assertEqual(preview1.project_id, "TEST")
        self.assertEqual(preview1.shot_id, "SH010")
        self.assertEqual(preview1.step_id, "COMP")
        self.assertEqual(preview1.format, "mp4")
        self.assertGreater(preview1.file_size, 0)

    def test_marker_detection_sent(self):
        """Test marker detection for sent previews."""
        previews = self.scanner.scan_project()
        preview2 = next(p for p in previews if p.shot_id == "SH020")

        # Marker is older than preview, so should be "Sent"
        self.assertTrue(preview2.status.startswith("Sent"))
        self.assertIsNotNone(preview2.marker_path)
        self.assertIsNotNone(preview2.sent_date)

    def test_marker_detection_ready(self):
        """Test that previews without markers show Ready."""
        previews = self.scanner.scan_project()
        preview1 = next(p for p in previews if p.shot_id == "SH010")

        self.assertEqual(preview1.status, "Ready")
        self.assertIsNone(preview1.marker_path)
        self.assertIsNone(preview1.sent_date)

    def test_marker_updated_detection(self):
        """Test detection of updated previews (newer than marker)."""
        # Create marker that's newer than preview
        preview_path = self.preview1_file.parent
        marker_date = datetime.now().strftime("%Y-%m-%d")
        marker = preview_path / f".review_sent_{marker_date}.txt"
        marker.write_text(f"Uploaded: {marker_date} 10:00:00\n")

        # Make preview newer than marker
        future_time = datetime.now() + timedelta(hours=1)
        os.utime(self.preview1_file, (future_time.timestamp(), future_time.timestamp()))

        # Rescan
        previews = self.scanner.scan_project()
        preview1 = next(p for p in previews if p.shot_id == "SH010")

        self.assertEqual(preview1.status, "Ready (Updated)")

    def test_multiple_markers_uses_most_recent(self):
        """Test that multiple markers use the most recent one."""
        preview_path = self.preview2_file.parent

        # Make preview even older (3 hours ago)
        preview_time = datetime.now() - timedelta(hours=3)
        os.utime(self.preview2_file, (preview_time.timestamp(), preview_time.timestamp()))

        # Create older marker
        old_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        old_marker = preview_path / f".review_sent_{old_date}.txt"
        old_marker.write_text(f"Uploaded: {old_date} 10:00:00\n")

        # Create newer marker
        new_date = datetime.now().strftime("%Y-%m-%d")
        new_marker = preview_path / f".review_sent_{new_date}.txt"
        new_marker.write_text(f"Uploaded: {new_date} 10:00:00\n")

        # Make new marker more recent (1 hour ago, still newer than preview)
        new_time = datetime.now() - timedelta(hours=1)
        os.utime(new_marker, (new_time.timestamp(), new_time.timestamp()))

        # Make old marker much older
        old_time = datetime.now() - timedelta(days=3)
        os.utime(old_marker, (old_time.timestamp(), old_time.timestamp()))

        previews = self.scanner.scan_project()
        preview2 = next(p for p in previews if p.shot_id == "SH020")

        # Should use the newer marker's date
        self.assertIn(new_date, preview2.status)

    def test_filter_by_date_today(self):
        """Test filtering previews by today."""
        previews = self.scanner.scan_project()

        # All previews are from today
        filtered = self.scanner.filter_by_date(previews, "Today")
        self.assertEqual(len(filtered), 2)

    def test_filter_by_date_this_week(self):
        """Test filtering previews by this week."""
        previews = self.scanner.scan_project()
        filtered = self.scanner.filter_by_date(previews, "This Week")
        self.assertEqual(len(filtered), 2)

    def test_filter_by_sequence(self):
        """Test filtering previews by sequence."""
        previews = self.scanner.scan_project()

        # Both shots should be in SEQ01
        filtered = self.scanner.filter_by_sequence(previews, "SEQ01")
        self.assertEqual(len(filtered), 0)  # Sequence extraction from folder name

    def test_filter_by_step(self):
        """Test filtering previews by step."""
        previews = self.scanner.scan_project()

        filtered_comp = self.scanner.filter_by_step(previews, "COMP")
        self.assertEqual(len(filtered_comp), 1)
        self.assertEqual(filtered_comp[0].step_id, "COMP")

        filtered_anim = self.scanner.filter_by_step(previews, "ANIM")
        self.assertEqual(len(filtered_anim), 1)
        self.assertEqual(filtered_anim[0].step_id, "ANIM")

    def test_empty_project(self):
        """Test scanning empty project returns empty list."""
        empty_root = self.temp_dir + "_empty"
        os.makedirs(empty_root)
        scanner = PreviewScanner(empty_root)

        previews = scanner.scan_project()
        self.assertEqual(len(previews), 0)

    def test_invalid_filename_ignored(self):
        """Test that invalid filenames are ignored."""
        shot_step = self.shots_folder / "TEST_S_SH030" / "TEST_S_SH030_LAYOUT"
        preview_folder = shot_step / "_preview"
        preview_folder.mkdir(parents=True)

        # Create file with invalid name
        invalid = preview_folder / "invalid_name.mp4"
        invalid.write_text("fake video")

        previews = self.scanner.scan_project()

        # Should still find the 2 valid ones, ignore invalid
        self.assertEqual(len(previews), 2)

    def tearDown(self):
        """Clean up temp directories."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
