"""Settings dialog for Ramses Out configuration."""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QGroupBox,
    QFormLayout,
    QFileDialog,
)
from PySide6.QtCore import Qt

from .stylesheet import STYLESHEET
from .config import load_ramses_settings, save_ramses_settings


class SettingsDialog(QDialog):
    """Settings configuration dialog."""

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config
        self.ramses_settings = load_ramses_settings()

        self.setWindowTitle("Ramses Out - Settings")
        self.setStyleSheet(STYLESHEET)
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # --- Out Settings ---
        review_group = QGroupBox("Out Settings")
        review_layout = QFormLayout(review_group)

        # Default collection path (relative to project)
        self.collection_path_edit = QLineEdit(config["review"].get("default_collection_path", ""))
        self.collection_path_edit.setPlaceholderText("e.g., for_review")
        review_layout.addRow("Default Collection Path:", self.collection_path_edit)

        # Help text
        help_label = QLabel("Relative to project root (e.g., 'for_review' creates PROJECT_ROOT/for_review)")
        help_label.setObjectName("statusLabel")
        help_label.setWordWrap(True)
        review_layout.addRow("", help_label)

        layout.addWidget(review_group)

        # --- Ramses Settings ---
        ramses_group = QGroupBox("Ramses Settings (Common)")
        ramses_layout = QFormLayout(ramses_group)

        # Ramses Client path (from common config)
        client_layout = QHBoxLayout()
        self.client_path_edit = QLineEdit(self.ramses_settings.get("clientPath", ""))
        self.client_path_edit.setPlaceholderText("Path to Ramses.exe")
        client_layout.addWidget(self.client_path_edit)
        browse_client_btn = QPushButton("Browse")
        browse_client_btn.clicked.connect(self._browse_client)
        client_layout.addWidget(browse_client_btn)
        ramses_layout.addRow("Ramses Client:", client_layout)

        # Daemon Port (from common config)
        self.daemon_port_edit = QLineEdit(str(self.ramses_settings.get("clientPort", 18185)))
        self.daemon_port_edit.setPlaceholderText("18185")
        ramses_layout.addRow("Daemon Port:", self.daemon_port_edit)

        layout.addWidget(ramses_group)

        layout.addStretch()

        # --- Buttons ---
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        save_btn = QPushButton("Save")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._save)
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def _browse_client(self):
        """Browse for Ramses client executable."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Ramses Client Executable",
            "",
            "Executables (*.exe);;All Files (*.*)"
        )

        if file_path:
            self.client_path_edit.setText(file_path)

    def _save(self):
        """Save settings to config."""
        # Save Out-specific settings
        collection_path = self.collection_path_edit.text().strip()
        # Normalize path separators
        if collection_path:
            collection_path = collection_path.replace("\\", "/")
            # Remove leading/trailing slashes
            collection_path = collection_path.strip("/")
        self.config["review"]["default_collection_path"] = collection_path

        # Save Ramses settings to common config (shared by all tools)
        client_port = 18185
        try:
            client_port = int(self.daemon_port_edit.text())
        except ValueError:
            pass

        save_ramses_settings(
            client_path=self.client_path_edit.text().strip(),
            client_port=client_port
        )

        self.accept()
