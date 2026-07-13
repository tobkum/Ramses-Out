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


def _preview(shot, step="COMP", db_state="", db_color="", file_size=1024):
    return PreviewItem(
        shot_id=shot,
        sequence_id="SEQ01",
        step_id=step,
        project_id="TEST",
        file_path=f"/proj/{shot}.mp4",
        file_size=file_size,
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

    def test_thumbnail_icon_on_shot_item(self):
        """Previews with a thumbnail render it as the Shot item's icon."""
        import tempfile, shutil
        tmp = tempfile.mkdtemp()
        try:
            # A real (tiny) image file so QIcon can decode it
            from PySide6.QtGui import QImage
            thumb = os.path.join(tmp, "thumb.jpg")
            img = QImage(8, 8, QImage.Format.Format_RGB32)
            img.fill(0xFF808080)
            img.save(thumb, "JPG")

            self.window.all_previews[0].thumbnail_path = thumb
            self.window._apply_filters()

            table = self.window.table
            row = next(r for r in range(table.rowCount()) if table.item(r, 1).text() == "SH010")
            self.assertFalse(table.item(row, 1).icon().isNull())
            # Rows without a thumbnail have no icon
            other = next(r for r in range(table.rowCount()) if table.item(r, 1).text() == "SH020")
            self.assertTrue(table.item(other, 1).icon().isNull())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_table_is_not_editable(self):
        """Double-click must play the preview — never open a cell editor.
        The table is display-only; edits would be silently discarded."""
        from PySide6.QtWidgets import QAbstractItemView
        self.assertEqual(
            self.window.table.editTriggers(),
            QAbstractItemView.EditTrigger.NoEditTriggers,
        )

    def test_double_click_plays_preview(self):
        from unittest.mock import patch
        self.window._apply_filters()
        target = self.window.filtered_previews[1]
        with patch.object(self.window, "_open_file") as mock_open:
            self.window._on_cell_double_clicked(1, 3)
        mock_open.assert_called_once_with(target.file_path)

    def test_double_click_on_checkbox_column_does_not_play(self):
        from unittest.mock import patch
        self.window._apply_filters()
        with patch.object(self.window, "_open_file") as mock_open:
            self.window._on_cell_double_clicked(0, 0)
        mock_open.assert_not_called()

    def test_apply_db_states_fills_previews_from_status_map(self):
        self.window.status_map = {("SH030", "COMP"): ("OK", "#00aa00")}
        changed = self.window._apply_db_states(self.window.all_previews)
        self.assertTrue(changed)
        sh030 = next(p for p in self.window.all_previews if p.shot_id == "SH030")
        self.assertEqual(sh030.db_state, "OK")
        # Second application is a no-op
        self.assertFalse(self.window._apply_db_states(self.window.all_previews))


@unittest.skipUnless(HAS_QT, "PySide6 not available")
class TestSortingAndSelection(unittest.TestCase):
    """Sorting-safe checkboxes and row mapping (same pattern as Ramses-Ingest:
    checkable items, not cell widgets — widgets don't move when Qt sorts)."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from PySide6.QtCore import Qt
        self.Qt = Qt
        from ramses_out.gui import RamsesOutWindow
        self.window = RamsesOutWindow()
        self.window.all_previews = [
            _preview("SH010", file_size=100 * 1024 * 1024),  # 100.0 MB
            _preview("SH020", file_size=int(9.5 * 1024 * 1024)),  # 9.5 MB
            _preview("SH030", file_size=1024),
        ]
        self.window._apply_filters()

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()

    def _row_of(self, shot):
        table = self.window.table
        return next(
            r for r in range(table.rowCount()) if table.item(r, 1).text() == shot
        )

    def _set_checked(self, shot, checked):
        state = self.Qt.CheckState.Checked if checked else self.Qt.CheckState.Unchecked
        self.window.table.item(self._row_of(shot), 0).setCheckState(state)

    def test_sorting_is_enabled(self):
        self.assertTrue(self.window.table.isSortingEnabled())

    def test_checkboxes_survive_sorting(self):
        """Check one row, sort descending — the check must follow the shot."""
        self.window._set_all_checked(False)
        self._set_checked("SH010", True)

        self.window.table.sortItems(1, self.Qt.SortOrder.DescendingOrder)

        # SH010 is now the last row, and still the only checked one
        checked = {
            self.window.table.item(r, 1).text()
            for r in range(self.window.table.rowCount())
            if self.window.table.item(r, 0).checkState() == self.Qt.CheckState.Checked
        }
        self.assertEqual(checked, {"SH010"})

        selected = self.window._get_selected_items()
        self.assertEqual([p.shot_id for p in selected], ["SH010"])

    def test_double_click_after_sorting_plays_correct_file(self):
        from unittest.mock import patch
        self.window.table.sortItems(1, self.Qt.SortOrder.DescendingOrder)
        row = self._row_of("SH020")
        with patch.object(self.window, "_open_file") as mock_open:
            self.window._on_cell_double_clicked(row, 3)
        mock_open.assert_called_once_with("/proj/SH020.mp4")

    def test_size_column_sorts_numerically(self):
        """9.5 must sort below 100 (lexical text would put '100' first)."""
        self.window.table.sortItems(6, self.Qt.SortOrder.AscendingOrder)
        table = self.window.table
        sizes = [table.item(r, 6).data(self.Qt.ItemDataRole.DisplayRole)
                 for r in range(table.rowCount())]
        self.assertEqual(sizes, sorted(sizes))
        # Largest file (SH010, 100 MB) ends up last
        self.assertEqual(table.item(table.rowCount() - 1, 1).text(), "SH010")

    def test_select_all_and_toggle(self):
        self.window._select_all()
        self.assertEqual(len(self.window._get_selected_items()), 3)

        self.window._deselect_all()
        self.assertEqual(len(self.window._get_selected_items()), 0)

        self.window.table.setCurrentCell(self._row_of("SH020"), 1)
        self.window._toggle_selected_row()
        self.assertEqual(
            [p.shot_id for p in self.window._get_selected_items()], ["SH020"]
        )


if __name__ == "__main__":
    unittest.main()
