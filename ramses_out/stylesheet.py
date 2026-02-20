"""Unified stylesheet for Ramses Out - matches Ramses-Ingest theme."""

# Dark theme with darker blue (#0a7fad) accents
STYLESHEET = """
QMainWindow {
    background-color: #121212;
}

QWidget {
    background-color: #121212;
    color: #e0e0e0;
}

QDialog {
    background-color: #121212;
}

/* --- Labels --- */
QLabel {
    color: #cccccc;
    background-color: transparent;
    font-size: 12px;
}

QLabel#headerLabel {
    font-size: 14px;
    font-weight: bold;
    color: #ffffff;
    letter-spacing: 0.5px;
    background-color: transparent;
}

QLabel#toolLabel {
    font-size: 12px;
    font-weight: bold;
    color: #ffffff;
    background-color: transparent;
}

QLabel#statusLabel {
    font-size: 10px;
    color: #888888;
    background-color: transparent;
    font-weight: bold;
}

QLabel#statusReady {
    color: #27ae60;
    font-weight: bold;
}

QLabel#statusWarning {
    color: #f39c12;
    font-weight: bold;
}

QLabel#statusError {
    color: #f44747;
    font-weight: bold;
}

QLabel#statusConnected {
    color: #27ae60;
    font-weight: bold;
    background-color: transparent;
}

QLabel#statusConnecting {
    color: #f39c12;
    font-weight: bold;
    background-color: transparent;
}

QLabel#statusDisconnected {
    color: #f44747;
    background-color: transparent;
}

/* --- Buttons --- */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #333333, stop:1 #2d2d2d);
    border: 1px solid #444444;
    border-radius: 4px;
    padding: 8px 16px;
    color: #e0e0e0;
    font-weight: 500;
    font-size: 12px;
}

QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3d3d3d, stop:1 #333333);
    border-color: #0a7fad;
}

QPushButton:pressed {
    background-color: #094771;
    color: white;
}

QPushButton:disabled {
    background: #1e1e1e;
    color: #555555;
    border-color: #2d2d2d;
}

/* Primary action button */
QPushButton#primaryButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0a7fad, stop:1 #094771);
    border: none;
    color: #ffffff;
    font-weight: bold;
    font-size: 13px;
    padding: 10px 24px;
}

QPushButton#primaryButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0d95c7, stop:1 #0a7fad);
}

QPushButton#primaryButton:disabled {
    background: #252526;
    color: #555555;
}

/* Tool card button */
QPushButton#toolCard {
    background-color: #1e1e1e;
    border: 2px solid #2d2d2d;
    border-radius: 8px;
    padding: 20px;
    text-align: left;
    color: #e0e0e0;
    min-height: 100px;
}

QPushButton#toolCard:hover {
    border-color: #0a7fad;
    background-color: #252526;
}

QPushButton#toolCard:pressed {
    background-color: #2d2d2d;
}

/* --- Inputs --- */
QLineEdit {
    background-color: #1e1e1e;
    border: 1px solid #333333;
    border-radius: 4px;
    padding: 6px 12px;
    color: #ffffff;
    font-size: 12px;
}

QLineEdit:focus {
    border-color: #0a7fad;
    background-color: #252526;
}

QComboBox {
    background-color: #1e1e1e;
    border: 1px solid #333333;
    border-radius: 4px;
    padding: 6px 12px;
    color: #e0e0e0;
}

QComboBox:hover {
    border-color: #444444;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #1e1e1e;
    border: 1px solid #444444;
    selection-background-color: #094771;
    color: #e0e0e0;
}

QCheckBox {
    spacing: 8px;
    background-color: transparent;
    color: #e0e0e0;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #555555;
    background-color: #1e1e1e;
    border-radius: 3px;
}

QCheckBox::indicator:checked {
    background-color: #094771;
    border-color: #094771;
}

QCheckBox::indicator:hover {
    border-color: #0a7fad;
}

/* --- Frames/Panels --- */
QFrame {
    background-color: transparent;
    border: none;
}

QFrame#panel {
    background-color: #1a1a1a;
    border: 1px solid #2d2d2d;
    border-radius: 8px;
    padding: 16px;
}

QFrame#separator {
    background-color: #333333;
    max-height: 1px;
}

/* --- Group Box --- */
QGroupBox {
    border: 1px solid #333333;
    border-radius: 4px;
    margin-top: 12px;
    padding-top: 12px;
    color: #cccccc;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    background-color: #121212;
    color: #0a7fad;
}

/* --- Text Edit --- */
QTextEdit {
    background-color: #1e1e1e;
    border: 1px solid #333333;
    border-radius: 4px;
    padding: 8px;
    color: #ffffff;
}

QTextEdit:focus {
    border-color: #0a7fad;
}

/* --- Scroll Bars --- */
QScrollBar:vertical {
    background-color: #1e1e1e;
    width: 12px;
    border: none;
}

QScrollBar::handle:vertical {
    background-color: #3d3d3d;
    border-radius: 6px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #555555;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #1e1e1e;
    height: 12px;
    border: none;
}

QScrollBar::handle:horizontal {
    background-color: #3d3d3d;
    border-radius: 6px;
    min-width: 20px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #555555;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* --- Status Cards --- */
QFrame#statusCard {
    background-color: #1a1a1a;
    border: 1px solid #2d2d2d;
    border-radius: 6px;
}

QFrame#statusCard:hover {
    border-color: #3d3d3d;
}

/* --- Menu --- */
QMenu {
    background-color: #252526;
    border: 1px solid #444444;
    padding: 4px;
}

QMenu::item {
    padding: 8px 24px;
    color: #e0e0e0;
}

QMenu::item:selected {
    background-color: #094771;
}

QMenu::separator {
    height: 1px;
    background: #3d3d3d;
    margin: 4px 8px;
}

/* --- Tool Tips --- */
QToolTip {
    background-color: #252526;
    border: 1px solid #444444;
    color: #e0e0e0;
    padding: 4px 8px;
}

/* --- Table Widget --- */
QTableWidget {
    background-color: #1a1a1a;
    border: 1px solid #2d2d2d;
    gridline-color: #2d2d2d;
    selection-background-color: #094771;
    selection-color: #ffffff;
    alternate-background-color: #1e1e1e;
    font-size: 12px;
}

QTableWidget::item {
    padding: 6px;
    font-size: 12px;
}

QTableWidget::item:selected {
    background-color: #094771;
}

QTableWidget::item:hover {
    background-color: #252526;
}

QHeaderView::section {
    background-color: #2d2d2d;
    color: #cccccc;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #444444;
    border-right: 1px solid #1a1a1a;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QHeaderView::section:horizontal {
    border-bottom: 1px solid #444444;
}

QHeaderView::section:hover {
    background-color: #252526;
}
"""
