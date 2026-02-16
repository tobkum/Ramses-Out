"""End-to-end integration tests for Ramses Out workflow."""

import os
import sys
import unittest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ramses_out.scanner import PreviewScanner
from ramses_out.tracker import UploadTracker
from ramses_out.collector import PreviewCollector


class TestEndToEndWorkflow(unittest.TestCase):
    """Test complete review workflow from scan to upload."""

    def setUp(self):
        """Create realistic project structure."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)

        # Create realistic Ramses project structure
        self.shots_folder = self.project_root / "05-SHOTS"

        # SEQ01 shots
        for shot_num in ["010", "020", "030"]:
            shot_id = f"SH{shot_num}"
            for step in ["ANIM", "COMP"]:
                shot_step = self.shots_folder / f"TEST_S_{shot_id}" / f"TEST_S_{shot_id}_{step}"
                preview_folder = shot_step / "_preview"
                preview_folder.mkdir(parents=True)

                # Create preview file
                preview_file = preview_folder / f"TEST_S_{shot_id}_{step}.mp4"
                preview_file.write_bytes(b"fake video data" * 1000)

        self.dest_dir = self.project_root / "for_review"
        self.dest_dir.mkdir()

    def test_full_workflow_first_upload(self):
        """Test complete workflow: scan → collect → mark as sent."""
        # Step 1: Scan project
        scanner = PreviewScanner(str(self.project_root))
        previews = scanner.scan_project()

        self.assertEqual(len(previews), 6)  # 3 shots × 2 steps

        # Step 2: Filter to COMP only
        comp_previews = scanner.filter_by_step(previews, "COMP")
        self.assertEqual(len(comp_previews), 3)

        # Step 3: Verify all are "Ready" (first time)
        for preview in comp_previews:
            self.assertEqual(preview.status, "Ready")
            self.assertTrue(preview.is_ready)

        # Step 4: Collect files
        collector = PreviewCollector()
        package_dir = self.dest_dir / "TEST_20260211"
        package_dir.mkdir()

        success, failed_files = collector.collect_files(comp_previews, str(package_dir))
        self.assertTrue(success)

        # Verify files copied
        copied_files = list(package_dir.glob("*.mp4"))
        self.assertEqual(len(copied_files), 3)

        # Step 5: Generate shot list
        success = collector.save_shot_list(comp_previews, str(package_dir), "TEST_PROJECT")
        self.assertTrue(success)

        shot_list = package_dir / "shot_list.txt"
        self.assertTrue(shot_list.exists())

        # Step 6: Mark as sent
        tracker = UploadTracker()
        tracker.history_log = self.project_root / "test_history.log"

        success = tracker.mark_as_sent(comp_previews, "TEST_20260211", "First review")
        self.assertTrue(success)

        # Verify markers created
        for preview in comp_previews:
            preview_folder = Path(preview.file_path).parent
            markers = list(preview_folder.glob(".review_sent_*.txt"))
            self.assertEqual(len(markers), 1)

        # Step 7: Rescan and verify status changed
        previews_after = scanner.scan_project()
        comp_after = scanner.filter_by_step(previews_after, "COMP")

        for preview in comp_after:
            self.assertTrue(preview.status.startswith("Sent"))
            self.assertFalse(preview.is_ready)

    def test_workflow_with_updated_previews(self):
        """Test workflow when previews are updated after first upload."""
        scanner = PreviewScanner(str(self.project_root))
        tracker = UploadTracker()
        tracker.history_log = self.project_root / "test_history.log"
        collector = PreviewCollector()

        # First upload
        previews = scanner.scan_project()
        comp_previews = scanner.filter_by_step(previews, "COMP")

        package1 = self.dest_dir / "TEST_20260211_V1"
        package1.mkdir()
        collector.collect_files(comp_previews, str(package1))
        tracker.mark_as_sent(comp_previews, "TEST_20260211_V1")

        # Update one preview (make it newer)
        shot010_preview = next(p for p in comp_previews if p.shot_id == "SH010")
        preview_file = Path(shot010_preview.file_path)

        # Make file newer
        future_time = datetime.now() + timedelta(hours=1)
        os.utime(preview_file, (future_time.timestamp(), future_time.timestamp()))

        # Rescan
        previews_after = scanner.scan_project()
        comp_after = scanner.filter_by_step(previews_after, "COMP")

        # Find updated preview
        sh010_after = next(p for p in comp_after if p.shot_id == "SH010")
        sh020_after = next(p for p in comp_after if p.shot_id == "SH020")

        # SH010 should be "Ready (Updated)", others "Sent"
        self.assertEqual(sh010_after.status, "Ready (Updated)")
        self.assertTrue(sh010_after.is_ready)
        self.assertTrue(sh020_after.status.startswith("Sent"))
        self.assertFalse(sh020_after.is_ready)

        # Collect only updated preview
        updated_previews = [p for p in comp_after if p.is_ready]
        self.assertEqual(len(updated_previews), 1)

        package2 = self.dest_dir / "TEST_20260211_V2"
        package2.mkdir()
        collector.collect_files(updated_previews, str(package2))
        tracker.mark_as_sent(updated_previews, "TEST_20260211_V2")

        # Verify history
        history = tracker.get_history("SH010")
        self.assertEqual(len(history), 2)  # Two uploads for SH010

    def test_workflow_with_filtering(self):
        """Test workflow with date and step filtering."""
        scanner = PreviewScanner(str(self.project_root))

        # Scan all
        all_previews = scanner.scan_project()
        self.assertEqual(len(all_previews), 6)

        # Filter by today
        today_previews = scanner.filter_by_date(all_previews, "Today")
        self.assertEqual(len(today_previews), 6)

        # Filter by step
        anim_previews = scanner.filter_by_step(all_previews, "ANIM")
        self.assertEqual(len(anim_previews), 3)

        comp_previews = scanner.filter_by_step(all_previews, "COMP")
        self.assertEqual(len(comp_previews), 3)

        # Combined filtering
        today_comp = scanner.filter_by_step(
            scanner.filter_by_date(all_previews, "Today"), "COMP"
        )
        self.assertEqual(len(today_comp), 3)

    def test_workflow_with_cancellation(self):
        """Test collection cancellation mid-workflow."""
        scanner = PreviewScanner(str(self.project_root))
        collector = PreviewCollector()

        previews = scanner.scan_project()

        package_dir = self.dest_dir / "TEST_CANCELLED"
        package_dir.mkdir()

        # Cancel after first file
        cancel_after = [0]

        def cancel_check():
            cancel_after[0] += 1
            return cancel_after[0] > 2  # Cancel after 2 files

        success, failed_files = collector.collect_files(
            previews, str(package_dir), cancel_check=cancel_check
        )

        # Should fail due to cancellation
        self.assertFalse(success)

        # Some files might have been copied before cancellation
        copied_files = list(package_dir.glob("*.mp4"))
        self.assertLess(len(copied_files), len(previews))

    def test_workflow_smart_defaults(self):
        """Test that smart defaults select correct previews."""
        scanner = PreviewScanner(str(self.project_root))
        tracker = UploadTracker()
        tracker.history_log = self.project_root / "test_history.log"

        # First scan - all should be ready
        previews = scanner.scan_project()
        ready_previews = [p for p in previews if p.is_ready]
        self.assertEqual(len(ready_previews), 6)  # All are ready

        # Mark half as sent
        comp_previews = scanner.filter_by_step(previews, "COMP")
        tracker.mark_as_sent(comp_previews, "TEST_20260211")

        # Rescan
        previews_after = scanner.scan_project()
        ready_after = [p for p in previews_after if p.is_ready]

        # Only ANIM shots should be ready now
        self.assertEqual(len(ready_after), 3)
        for preview in ready_after:
            self.assertEqual(preview.step_id, "ANIM")

    def tearDown(self):
        """Clean up temp directories."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
