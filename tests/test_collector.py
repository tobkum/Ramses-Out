"""Tests for file collection and shot list generation."""

import os
import sys
import unittest
import tempfile
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ramses_review.collector import PreviewCollector
from ramses_review.models import PreviewItem


class TestPreviewCollector(unittest.TestCase):
    """Test file collection and shot list generation."""

    def setUp(self):
        """Create temp directories and collector."""
        self.temp_dir = tempfile.mkdtemp()
        self.source_dir = Path(self.temp_dir) / "source"
        self.dest_dir = Path(self.temp_dir) / "dest"

        self.source_dir.mkdir()
        self.dest_dir.mkdir()

        # Create test preview files
        self.preview1 = self.source_dir / "TEST_S_SH010_COMP.mp4"
        self.preview1.write_text("video data 1" * 100)

        self.preview2 = self.source_dir / "TEST_S_SH020_ANIM.mp4"
        self.preview2.write_text("video data 2" * 200)

        self.collector = PreviewCollector()

    def create_preview_item(self, file_path, shot_id, step_id):
        """Create a test PreviewItem."""
        file_path = Path(file_path)
        return PreviewItem(
            shot_id=shot_id,
            sequence_id="SEQ01",
            step_id=step_id,
            project_id="TEST",
            file_path=str(file_path),
            file_size=file_path.stat().st_size,
            date_modified=datetime.now(),
            format="mp4",
            status="Ready",
        )

    def test_collect_files_success(self):
        """Test successful file collection."""
        items = [
            self.create_preview_item(self.preview1, "SH010", "COMP"),
            self.create_preview_item(self.preview2, "SH020", "ANIM"),
        ]

        success = self.collector.collect_files(items, str(self.dest_dir))

        self.assertTrue(success)

        # Verify files were copied
        copied1 = self.dest_dir / "TEST_S_SH010_COMP.mp4"
        copied2 = self.dest_dir / "TEST_S_SH020_ANIM.mp4"

        self.assertTrue(copied1.exists())
        self.assertTrue(copied2.exists())
        self.assertEqual(copied1.stat().st_size, self.preview1.stat().st_size)

    def test_collect_with_progress_callback(self):
        """Test collection with progress tracking."""
        items = [
            self.create_preview_item(self.preview1, "SH010", "COMP"),
            self.create_preview_item(self.preview2, "SH020", "ANIM"),
        ]

        progress_calls = []

        def progress_callback(current, total, filename):
            progress_calls.append((current, total, filename))

        success = self.collector.collect_files(
            items, str(self.dest_dir), progress_callback=progress_callback
        )

        self.assertTrue(success)
        self.assertEqual(len(progress_calls), 2)
        self.assertEqual(progress_calls[0][0], 1)  # First file
        self.assertEqual(progress_calls[1][0], 2)  # Second file
        self.assertEqual(progress_calls[0][1], 2)  # Total

    def test_collect_with_cancellation(self):
        """Test collection can be cancelled."""
        items = [
            self.create_preview_item(self.preview1, "SH010", "COMP"),
            self.create_preview_item(self.preview2, "SH020", "ANIM"),
        ]

        call_count = [0]

        def cancel_check():
            call_count[0] += 1
            return call_count[0] > 1  # Cancel after first file

        success = self.collector.collect_files(
            items, str(self.dest_dir), cancel_check=cancel_check
        )

        self.assertFalse(success)  # Should return False on cancellation

    def test_collect_missing_file(self):
        """Test collection handles missing source files."""
        # Create PreviewItem manually for missing file
        missing_item = PreviewItem(
            shot_id="SH030",
            sequence_id="SEQ01",
            step_id="LAYOUT",
            project_id="TEST",
            file_path=str(self.source_dir / "missing.mp4"),
            file_size=1024,
            date_modified=datetime.now(),
            format="mp4",
            status="Ready",
        )

        items = [
            self.create_preview_item(self.preview1, "SH010", "COMP"),
            missing_item,
        ]

        success = self.collector.collect_files(items, str(self.dest_dir))

        # Should fail if any files are missing
        self.assertFalse(success)

        # But first file should have been copied
        copied1 = self.dest_dir / "TEST_S_SH010_COMP.mp4"
        self.assertTrue(copied1.exists())

    def test_collect_creates_destination(self):
        """Test collection creates destination if it doesn't exist."""
        new_dest = self.dest_dir / "subfolder" / "package"
        items = [self.create_preview_item(self.preview1, "SH010", "COMP")]

        success = self.collector.collect_files(items, str(new_dest))

        self.assertTrue(success)
        self.assertTrue(new_dest.exists())

    def test_generate_shot_list(self):
        """Test shot list generation."""
        items = [
            self.create_preview_item(self.preview1, "SH010", "COMP"),
            self.create_preview_item(self.preview2, "SH020", "ANIM"),
        ]

        shot_list = self.collector.generate_shot_list(items, "TEST_PROJECT")

        self.assertIn("TEST_PROJECT", shot_list)
        self.assertIn("SH010", shot_list)
        self.assertIn("SH020", shot_list)
        self.assertIn("COMP", shot_list)
        self.assertIn("ANIM", shot_list)
        self.assertIn("Total: 2 shots", shot_list)
        self.assertIn("SEQ01", shot_list)

    def test_shot_list_groups_by_sequence(self):
        """Test shot list groups shots by sequence."""
        items = [
            PreviewItem(
                shot_id="SH010",
                sequence_id="SEQ01",
                step_id="COMP",
                project_id="TEST",
                file_path=str(self.preview1),
                file_size=1024,
                date_modified=datetime.now(),
                format="mp4",
                status="Ready",
            ),
            PreviewItem(
                shot_id="SH030",
                sequence_id="SEQ02",
                step_id="ANIM",
                project_id="TEST",
                file_path=str(self.preview2),
                file_size=2048,
                date_modified=datetime.now(),
                format="mp4",
                status="Ready",
            ),
        ]

        shot_list = self.collector.generate_shot_list(items, "TEST_PROJECT")

        # Check both sequences appear
        self.assertIn("# SEQ01", shot_list)
        self.assertIn("# SEQ02", shot_list)

        # Check proper grouping
        lines = shot_list.split("\n")
        seq01_idx = next(i for i, l in enumerate(lines) if "# SEQ01" in l)
        seq02_idx = next(i for i, l in enumerate(lines) if "# SEQ02" in l)

        # SH010 should appear after SEQ01 header but before SEQ02
        sh010_idx = next(i for i, l in enumerate(lines) if "SH010" in l)
        self.assertTrue(seq01_idx < sh010_idx < seq02_idx)

    def test_save_shot_list(self):
        """Test saving shot list to file."""
        items = [self.create_preview_item(self.preview1, "SH010", "COMP")]

        success = self.collector.save_shot_list(items, str(self.dest_dir), "TEST_PROJECT")

        self.assertTrue(success)

        shot_list_file = self.dest_dir / "shot_list.txt"
        self.assertTrue(shot_list_file.exists())

        content = shot_list_file.read_text()
        self.assertIn("TEST_PROJECT", content)
        self.assertIn("SH010", content)

    def test_shot_list_shows_file_sizes(self):
        """Test shot list includes file sizes."""
        items = [self.create_preview_item(self.preview1, "SH010", "COMP")]

        shot_list = self.collector.generate_shot_list(items, "TEST_PROJECT")

        # Should show size in MB
        self.assertIn("MB", shot_list)
        self.assertIn("SH010", shot_list)

    def test_empty_collection(self):
        """Test collecting empty list."""
        items = []

        success = self.collector.collect_files(items, str(self.dest_dir))

        # Should fail with no items
        self.assertFalse(success)

    def tearDown(self):
        """Clean up temp directories."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
