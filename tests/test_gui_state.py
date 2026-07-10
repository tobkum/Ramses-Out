"""GUI tests for the DB State column and the approved-only filter (offscreen Qt)."""

import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
    HAS_QT = True
except ImportError:
    HAS_QT = False

from ramses_out.models import PreviewItem


def _preview(shot, step="COMP", db_state="", db_color=""):
    return PreviewItem(
        shot_id=shot,
        sequence_id="SEQ01",
        step_id=step,
        project_id="TEST",
        file_path=f"/proj/{shot}.mp4",
        file_size=1024,
        date_modified=datetime.now(),
        format="mp4",
        status="Ready",
        db_state=db_state,
        db_state_color=db_color,
    )


@unittest.skipUnless(HAS_QT, "PySide6 not available")
class TestStateColumnAndFilter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from ramses_out.gui import RamsesOutWindow
        self.window = RamsesOutWindow()
        self.window.all_previews = [
            _preview("SH010", db_state="OK", db_color="#00aa00"),
            _preview("SH020", db_state="WIP", db_color="#f39c12"),
            _preview("SH030"),  # no DB status
        ]

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()

    def test_state_column_rendered_with_color(self):
        self.window._apply_filters()
        table = self.window.table
        self.assertEqual(table.columnCount(), 8)
        self.assertEqual(table.rowCount(), 3)

        # Column 4 is the DB state
        states = {table.item(r, 1).text(): table.item(r, 4).text() for r in range(3)}
        self.assertEqual(states, {"SH010": "OK", "SH020": "WIP", "SH030": "—"})

        ok_row = next(r for r in range(3) if table.item(r, 1).text() == "SH010")
        self.assertEqual(table.item(ok_row, 4).foreground().color().name(), "#00aa00")

    def test_only_ok_filter(self):
        self.window.ok_filter.setChecked(True)  # triggers _apply_filters
        table = self.window.table
        self.assertEqual(table.rowCount(), 1)
        self.assertEqual(table.item(0, 1).text(), "SH010")

        self.window.ok_filter.setChecked(False)
        self.assertEqual(self.window.table.rowCount(), 3)

    def test_apply_db_states_fills_previews_from_status_map(self):
        self.window.status_map = {("SH030", "COMP"): ("OK", "#00aa00")}
        changed = self.window._apply_db_states(self.window.all_previews)
        self.assertTrue(changed)
        sh030 = next(p for p in self.window.all_previews if p.shot_id == "SH030")
        self.assertEqual(sh030.db_state, "OK")
        # Second application is a no-op
        self.assertFalse(self.window._apply_db_states(self.window.all_previews))


if __name__ == "__main__":
    unittest.main()
