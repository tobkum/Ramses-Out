"""Main GUI for Ramses Out."""

import sys
import os
from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QComboBox,
    QFileDialog,
    QMessageBox,
    QHeaderView,
    QCheckBox,
    QProgressDialog,
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QShortcut, QKeySequence

from .stylesheet import STYLESHEET
from .scanner import PreviewScanner
from .tracker import UploadTracker
from .collector import PreviewCollector
from .models import PreviewItem
from .config import load_config, save_config
from .settings_dialog import SettingsDialog

# Add lib path for Ramses
lib_path = Path(__file__).parent.parent.parent / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

from ramses import Ramses


class ScanThread(QThread):
    """Background thread for scanning project."""

    finished = Signal(list)  # Emits list of PreviewItem
    error = Signal(str)

    def __init__(self, project_root: str):
        super().__init__()
        self.project_root = project_root

    def run(self):
        """Run scan in background."""
        try:
            scanner = PreviewScanner(self.project_root)
            previews = scanner.scan_project()
            self.finished.emit(previews)
        except Exception as e:
            self.error.emit(str(e))


class CollectionThread(QThread):
    """Background thread for collecting files."""

    progress = Signal(int, int, str)  # current, total, filename
    finished = Signal(bool, list)  # success, failed_files
    error = Signal(str)

    def __init__(self, items: List[PreviewItem], dest: str):
        super().__init__()
        self.items = items
        self.dest = dest
        self._cancel_requested = False

    def cancel(self):
        """Request cancellation of the collection."""
        self._cancel_requested = True

    def run(self):
        """Run collection in background."""
        try:
            collector = PreviewCollector()
            success, failed_files = collector.collect_files(
                self.items,
                self.dest,
                progress_callback=self._emit_progress,
                cancel_check=lambda: self._cancel_requested
            )
            self.finished.emit(success, failed_files)
        except Exception as e:
            self.error.emit(str(e))

    def _emit_progress(self, current: int, total: int, filename: str):
        """Emit progress signal."""
        self.progress.emit(current, total, filename)


class ConnectionWorker(QThread):
    """Connects to Ramses daemon in a background thread."""

    finished = Signal(bool)

    def run(self):
        try:
            ram = Ramses.instance()
            if not ram.online():
                ram.connect()
            self.finished.emit(ram.online() and ram.project() is not None)
        except Exception:
            self.finished.emit(False)


class RamsesOutWindow(QMainWindow):
    """Main window for Ramses Out."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ramses Out")
        self.setStyleSheet(STYLESHEET)
        self.resize(1000, 700)

        # Initialize Ramses API (connection happens async below)
        self.ramses = Ramses.instance()
        self.current_project = None

        # Load configuration
        self.config = load_config()

        # Cache sequences, steps, and shot→sequence map from API (source of truth)
        self.api_sequences: List[str] = []
        self.api_steps: List[str] = []
        self.shot_seq_map: dict = {}

        # Data
        self.all_previews: List[PreviewItem] = []
        self.filtered_previews: List[PreviewItem] = []
        self.scanner = None
        self.tracker = UploadTracker()
        self.collector = PreviewCollector()

        # Threads
        self.scan_thread: Optional[ScanThread] = None
        self.collection_thread: Optional[CollectionThread] = None
        self._connection_worker: Optional[ConnectionWorker] = None

        # Auto-reconnect timer
        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setInterval(5000)
        self._reconnect_timer.timeout.connect(self._try_connect)

        # Build UI
        self._build_ui()

        # Connect asynchronously on startup
        QTimer.singleShot(100, self._try_connect)

    def _cache_api_data(self):
        """Cache sequences and steps from Ramses API (source of truth)."""
        if not self.current_project:
            return

        try:
            # Get all sequences from API and build shot→sequence map
            sequences = self.current_project.sequences()
            self.api_sequences = []
            self.shot_seq_map = {}
            for seq in sequences:
                seq_name = seq.shortName()
                if seq_name:
                    self.api_sequences.append(seq_name)
                for shot in seq.shots():
                    shot_name = shot.shortName()
                    if shot_name and seq_name:
                        self.shot_seq_map[shot_name] = seq_name

            # Get all shot production steps from API
            from ramses import StepType
            steps = self.current_project.steps(StepType.SHOT_PRODUCTION)
            self.api_steps = [step.shortName() for step in steps if step.shortName()]
        except Exception as e:
            print(f"Warning: Failed to cache API data: {e}")
            self.api_sequences = []
            self.api_steps = []
            self.shot_seq_map = {}

    def _populate_filter_dropdowns(self):
        """Populate filter dropdowns from API data (source of truth)."""
        # Populate sequence filter from API
        self.seq_filter.clear()
        self.seq_filter.addItem("All Sequences")
        for seq in sorted(self.api_sequences):
            self.seq_filter.addItem(seq)

        # Populate step filter from API
        self.step_filter.clear()
        self.step_filter.addItem("All Steps")
        for step in sorted(self.api_steps):
            self.step_filter.addItem(step)

    def _build_ui(self):
        """Build the user interface."""
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header
        header = QLabel("Ramses Out")
        header.setObjectName("headerLabel")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Project info bar
        info_layout = QHBoxLayout()

        # Daemon status indicator
        self._status_label = QLabel("OFFLINE")
        self._status_label.setObjectName("statusDisconnected")
        self._status_label.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        info_layout.addWidget(self._status_label)

        self._btn_reconnect = QPushButton("Reconnect")
        self._btn_reconnect.setFixedWidth(80)
        self._btn_reconnect.setFixedHeight(22)
        self._btn_reconnect.setStyleSheet("font-size: 9px; padding: 2px;")
        self._btn_reconnect.clicked.connect(self._try_connect)
        self._btn_reconnect.setVisible(False)
        info_layout.addWidget(self._btn_reconnect)

        self._btn_refresh_connection = QPushButton("↻ Refresh")
        self._btn_refresh_connection.setFixedWidth(70)
        self._btn_refresh_connection.setFixedHeight(22)
        self._btn_refresh_connection.setStyleSheet("font-size: 9px; padding: 2px;")
        self._btn_refresh_connection.clicked.connect(self._try_connect)
        self._btn_refresh_connection.setVisible(False)
        info_layout.addWidget(self._btn_refresh_connection)

        sep = QLabel("|")
        sep.setStyleSheet("color: #444444;")
        info_layout.addWidget(sep)

        info_layout.addWidget(QLabel("Project:"))
        self.project_label = QLabel("—")
        self.project_label.setStyleSheet("color: #ffffff; font-weight: 800; font-size: 13px;")
        info_layout.addWidget(self.project_label)

        info_layout.addStretch()

        self.last_scan_label = QLabel("Last Scan: Never")
        self.last_scan_label.setObjectName("statusLabel")
        info_layout.addWidget(self.last_scan_label)

        layout.addLayout(info_layout)

        # Filters
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(12)

        filter_layout.addWidget(QLabel("Filter:"))

        self.date_filter = QComboBox()
        self.date_filter.addItems(["All", "Today", "This Week", "This Month"])
        self.date_filter.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.date_filter)

        self.seq_filter = QComboBox()
        self.seq_filter.addItem("All Sequences")
        self.seq_filter.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.seq_filter)

        self.step_filter = QComboBox()
        self.step_filter.addItem("All Steps")
        self.step_filter.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.step_filter)

        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "", "Shot", "Sequence", "Step", "Format", "Size (MB)", "Status"
        ])
        # Column sizing: Fixed widths for consistent layout
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 30)  # Checkbox
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.resizeSection(1, 100)  # Shot ID (e.g., SH010)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.resizeSection(2, 80)  # Sequence (e.g., SEQ01)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.resizeSection(3, 90)  # Step (COMP, LAYOUT, etc.)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        header.resizeSection(4, 70)  # Format (mp4, mov) - wider for uppercase header
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        header.resizeSection(5, 80)  # Size (MB)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)  # Status stretches
        self.table.verticalHeader().setDefaultSectionSize(42)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        # Selection info
        self.selection_label = QLabel("Selected: 0 shots")
        self.selection_label.setObjectName("statusLabel")
        layout.addWidget(self.selection_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        # Secondary actions on left
        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self._show_settings)
        button_layout.addWidget(settings_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._scan_project)
        button_layout.addWidget(refresh_btn)

        button_layout.addStretch()

        # Primary actions on right (matches Ramses-Ingest pattern)
        self.mark_sent_btn = QPushButton("Mark as Sent")
        self.mark_sent_btn.clicked.connect(self._mark_as_sent)
        self.mark_sent_btn.setEnabled(False)
        button_layout.addWidget(self.mark_sent_btn)

        self.collect_btn = QPushButton("Collect to Folder")
        self.collect_btn.setObjectName("primaryButton")
        self.collect_btn.clicked.connect(self._collect_to_folder)
        self.collect_btn.setEnabled(False)
        button_layout.addWidget(self.collect_btn)

        layout.addLayout(button_layout)

        # Setup keyboard shortcuts
        self._setup_shortcuts()

    def _setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        # F5 - Refresh scan
        refresh_shortcut = QShortcut(QKeySequence("F5"), self)
        refresh_shortcut.activated.connect(self._scan_project)

        # Ctrl+A - Select all
        select_all_shortcut = QShortcut(QKeySequence("Ctrl+A"), self)
        select_all_shortcut.activated.connect(self._select_all)

        # Ctrl+D - Deselect all
        deselect_all_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        deselect_all_shortcut.activated.connect(self._deselect_all)

        # Space - Toggle selected row
        toggle_shortcut = QShortcut(QKeySequence("Space"), self)
        toggle_shortcut.activated.connect(self._toggle_selected_row)

    def _select_all(self):
        """Select all checkboxes."""
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(True)
        self._update_selection_label()

    def _deselect_all(self):
        """Deselect all checkboxes."""
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(False)
        self._update_selection_label()

    def _toggle_selected_row(self):
        """Toggle checkbox of currently selected row."""
        current_row = self.table.currentRow()
        if current_row >= 0:
            checkbox_widget = self.table.cellWidget(current_row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(not checkbox.isChecked())
                    self._update_selection_label()

    def _show_settings(self):
        """Show settings dialog."""
        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            # Save config after dialog is accepted
            save_config(self.config)

    def _open_folder(self, folder_path: str):
        """Open folder in file manager (cross-platform)."""
        import platform
        import subprocess

        try:
            system = platform.system()
            if system == "Windows":
                os.startfile(folder_path)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", folder_path])
            else:  # Linux and others
                subprocess.run(["xdg-open", folder_path])
        except Exception as e:
            # If opening fails, just log it - not critical
            print(f"Could not open folder: {e}")

    def _try_connect(self):
        """Start background connection attempt to Ramses daemon."""
        if self._connection_worker and self._connection_worker.isRunning():
            return

        # Show connecting state
        self._status_label.setText("CONNECTING...")
        self._status_label.setObjectName("statusConnecting")
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)
        self._btn_reconnect.setVisible(False)
        self._btn_refresh_connection.setEnabled(False)

        self._connection_worker = ConnectionWorker(parent=self)
        self._connection_worker.finished.connect(self._on_connection_finished)
        self._connection_worker.start()

    def _on_connection_finished(self, ok: bool):
        """Handle daemon connection result."""
        if ok:
            self._reconnect_timer.stop()
            self._status_label.setText("DAEMON ONLINE")
            self._status_label.setObjectName("statusConnected")
            self._btn_reconnect.setVisible(False)
            self._btn_refresh_connection.setVisible(True)
            self._btn_refresh_connection.setEnabled(True)

            # Cache project data
            self.current_project = self.ramses.project()
            if self.current_project:
                pid = self.current_project.shortName()
                pname = self.current_project.name()
                self.project_label.setText(f"{pid} - {pname}")
            self._cache_api_data()
            self._populate_filter_dropdowns()

            # Enable action buttons
            self.mark_sent_btn.setEnabled(True)
            self.collect_btn.setEnabled(True)

            # Auto-scan on first successful connection
            if self.current_project:
                self._scan_project()
        else:
            self._status_label.setText("OFFLINE")
            self._status_label.setObjectName("statusDisconnected")
            self._btn_reconnect.setVisible(True)
            self._btn_refresh_connection.setVisible(False)
            self.project_label.setText("— (Connection Required)")

            # Disable action buttons
            self.mark_sent_btn.setEnabled(False)
            self.collect_btn.setEnabled(False)

            # Start auto-retry
            if not self._reconnect_timer.isActive():
                self._reconnect_timer.start()

        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)

    def _scan_project(self):
        """Scan project for preview files."""
        # Check if scan is already running
        if self.scan_thread and self.scan_thread.isRunning():
            return

        if not self.current_project:
            QMessageBox.warning(
                self,
                "No Project",
                "No active project found. Please open a project in Ramses Client."
            )
            return

        # Get project path
        project_path = self.current_project.folderPath()
        if not project_path or not Path(project_path).exists():
            QMessageBox.warning(
                self,
                "Invalid Project",
                f"Project path not found: {project_path}"
            )
            return

        # Start scan thread
        self.scan_thread = ScanThread(project_path)
        self.scan_thread.finished.connect(self._on_scan_finished)
        self.scan_thread.error.connect(self._on_scan_error)
        self.scan_thread.start()

        # Update UI
        self.last_scan_label.setText("Last Scan: Scanning...")
        self.table.setEnabled(False)

    def _on_scan_finished(self, previews: List[PreviewItem]):
        """Handle scan completion."""
        # Refresh API cache (sequences, steps, shot map) so dropdowns stay current
        self._cache_api_data()

        # Resolve sequence IDs from cached map
        for preview in previews:
            if not preview.sequence_id and preview.shot_id in self.shot_seq_map:
                preview.sequence_id = self.shot_seq_map[preview.shot_id]

        self.all_previews = previews
        self._populate_filter_dropdowns()
        self._apply_filters()

        # Update UI
        from datetime import datetime
        self.last_scan_label.setText(f"Last Scan: {datetime.now().strftime('%H:%M:%S')}")
        self.table.setEnabled(True)

    def _on_scan_error(self, error: str):
        """Handle scan error."""
        QMessageBox.critical(
            self,
            "Scan Error",
            f"Error scanning project: {error}"
        )
        self.table.setEnabled(True)

    def _apply_filters(self):
        """Apply current filters to preview list."""
        if not self.all_previews:
            self.filtered_previews = []
            self._populate_table()
            return

        # Apply filters
        filtered = self.all_previews

        # Date filter
        date_range = self.date_filter.currentText()
        filtered = PreviewScanner.filter_by_date(filtered, date_range)

        # Sequence filter
        seq = self.seq_filter.currentText()
        if seq != "All Sequences":
            filtered = PreviewScanner.filter_by_sequence(filtered, seq)

        # Step filter
        step = self.step_filter.currentText()
        if step != "All Steps":
            filtered = PreviewScanner.filter_by_step(filtered, step)

        self.filtered_previews = filtered
        self._populate_table()

    def _populate_table(self):
        """Populate table with filtered previews."""
        self.table.setRowCount(0)

        for item in self.filtered_previews:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Checkbox
            checkbox = QCheckBox()
            if item.is_ready:
                checkbox.setChecked(True)
            checkbox.stateChanged.connect(self._update_selection_label)
            checkbox_widget = QWidget()
            checkbox_widget.setStyleSheet("background: transparent;")
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(row, 0, checkbox_widget)

            # Data columns
            self.table.setItem(row, 1, QTableWidgetItem(item.shot_id))
            self.table.setItem(row, 2, QTableWidgetItem(item.sequence_id))
            self.table.setItem(row, 3, QTableWidgetItem(item.step_id))
            self.table.setItem(row, 4, QTableWidgetItem(item.format.upper()))
            self.table.setItem(row, 5, QTableWidgetItem(f"{item.size_mb:.1f}"))

            # Status with color
            status_item = QTableWidgetItem(item.status)
            if "Updated" in item.status:
                # Orange/yellow for updated previews that need re-upload
                status_item.setForeground(Qt.GlobalColor.yellow)
            elif item.is_ready:
                # Green for new previews
                status_item.setForeground(Qt.GlobalColor.green)
            else:
                # Gray for already sent
                status_item.setForeground(Qt.GlobalColor.gray)
            self.table.setItem(row, 6, status_item)

        self._update_selection_label()

    def _get_selected_items(self) -> List[PreviewItem]:
        """Get currently selected preview items."""
        selected = []
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    selected.append(self.filtered_previews[row])
        return selected

    def _update_selection_label(self):
        """Update selection count label."""
        selected = self._get_selected_items()
        total_size = sum(item.size_mb for item in selected)
        self.selection_label.setText(
            f"Selected: {len(selected)} shots ({total_size:.1f} MB)"
        )

    def _collect_to_folder(self):
        """Collect selected previews to a folder."""
        from datetime import datetime

        selected = self._get_selected_items()

        if not selected:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select at least one preview to collect."
            )
            return

        # Generate package name
        proj_name = self.current_project.shortName() if self.current_project else "UNKNOWN"
        package_name = f"{proj_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Determine destination folder
        default_path = self.config["review"].get("default_collection_path", "")

        if default_path and self.current_project:
            # Use default path relative to project root
            project_root = Path(self.current_project.folderPath())
            dest = project_root / default_path / package_name
            dest.mkdir(parents=True, exist_ok=True)
            dest = str(dest)
        else:
            # Choose destination folder via dialog
            dest = QFileDialog.getExistingDirectory(
                self,
                "Select Collection Folder",
                str(Path.home() / "Desktop")
            )

            if not dest:
                return

        # Create progress dialog
        progress = QProgressDialog("Collecting previews...", "Cancel", 0, len(selected), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setWindowTitle("Collecting")

        # Start collection thread
        self.collection_thread = CollectionThread(selected, dest)
        self.collection_thread.progress.connect(
            lambda curr, total, fname: self._on_collection_progress(progress, curr, total, fname)
        )
        self.collection_thread.finished.connect(
            lambda success, failed_files: self._on_collection_finished(success, failed_files, dest, selected, package_name, progress)
        )
        self.collection_thread.error.connect(
            lambda err: self._on_collection_error(err, progress)
        )
        # Connect cancel button
        progress.canceled.connect(self.collection_thread.cancel)
        self.collection_thread.start()

    def _on_collection_progress(self, dialog: QProgressDialog, current: int, total: int, filename: str):
        """Update collection progress."""
        dialog.setValue(current)
        dialog.setLabelText(f"Copying {filename}...")

    def _on_collection_finished(
        self,
        success: bool,
        failed_files: List[tuple[str, str]],
        dest: str,
        items: List[PreviewItem],
        package_name: str,
        dialog: QProgressDialog
    ):
        """Handle collection completion."""
        dialog.close()

        if success:
            # Generate shot list
            proj_name = self.current_project.shortName() if self.current_project else "UNKNOWN"
            self.collector.save_shot_list(items, dest, proj_name)

            QMessageBox.information(
                self,
                "Collection Complete",
                f"Successfully collected {len(items)} previews to:\n{dest}\n\n"
                f"Package: {package_name}"
            )

            # Open folder in file manager (cross-platform)
            self._open_folder(dest)
        elif self.collection_thread and self.collection_thread._cancel_requested:
            pass  # User cancelled — no error dialog needed
        elif failed_files:
            error_msg = "Failed to collect some files:\n\n"
            for fname, error in failed_files[:10]:  # Limit to 10
                error_msg += f"• {fname}: {error}\n"
            if len(failed_files) > 10:
                error_msg += f"\n...and {len(failed_files) - 10} more."
            QMessageBox.critical(self, "Collection Incomplete", error_msg)
        else:
            QMessageBox.critical(
                self,
                "Collection Failed",
                "Failed to collect files. Please check the destination folder."
            )

    def _on_collection_error(self, error: str, dialog: QProgressDialog):
        """Handle collection error."""
        dialog.close()
        QMessageBox.critical(
            self,
            "Collection Error",
            f"Error during collection: {error}"
        )

    def _mark_as_sent(self):
        """Mark selected previews as sent."""
        selected = self._get_selected_items()

        if not selected:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select at least one preview to mark as sent."
            )
            return

        # Generate package name
        from datetime import datetime
        proj_name = self.current_project.shortName() if self.current_project else "UNKNOWN"
        package_name = f"{proj_name}_{datetime.now().strftime('%Y%m%d')}"

        # Mark as sent
        success = self.tracker.mark_as_sent(selected, package_name)

        if success:
            QMessageBox.information(
                self,
                "Marked as Sent",
                f"Successfully marked {len(selected)} previews as sent."
            )
            # Refresh to update status
            self._scan_project()
        else:
            QMessageBox.critical(
                self,
                "Mark Failed",
                "Failed to mark some previews. Check file permissions."
            )


def main():
    """Entry point for Ramses Out."""
    app = QApplication(sys.argv)
    app.setApplicationName("Ramses Out")

    window = RamsesOutWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
