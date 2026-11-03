"""Application theme."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

STYLESHEET = """
QWidget {
    background-color: #1b1b22;
    color: #e7e7ee;
    font-family: "Segoe UI", "Noto Sans", sans-serif;
    font-size: 13px;
}
QMainWindow, QDialog { background-color: #1b1b22; }
QMenuBar { background-color: #22222b; }
QMenuBar::item:selected { background-color: #343445; }
QMenu { background-color: #24242e; border: 1px solid #3a3a4a; }
QMenu::item:selected { background-color: #3a3a4f; }
QPushButton {
    background-color: #2d2d3a;
    border: 1px solid #42425a;
    border-radius: 4px;
    padding: 6px 12px;
}
QPushButton:hover { background-color: #38384a; }
QPushButton:disabled { color: #6b6b7b; background-color: #24242d; }
QPushButton:pressed { background-color: #20202a; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit {
    background-color: #24242e;
    border: 1px solid #42425a;
    border-radius: 4px;
    padding: 4px 6px;
    selection-background-color: #3f6f9e;
}
QComboBox QAbstractItemView { background-color: #24242e; selection-background-color: #3f6f9e; }
QGroupBox {
    border: 1px solid #383848;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 8px;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #b8b8c8; }
QTabWidget::pane { border: 1px solid #383848; border-radius: 4px; }
QTabBar::tab { background-color: #24242e; padding: 7px 14px; margin-right: 2px; }
QTabBar::tab:selected { background-color: #343445; }
QProgressBar { border: 1px solid #42425a; border-radius: 4px; background-color: #24242e; }
QProgressBar::chunk { background-color: #3f6f9e; }
QSplitter::handle { background-color: #2a2a35; }
QStatusBar { background-color: #22222b; color: #a8a8b8; }
QScrollBar:vertical { background: #1b1b22; width: 12px; }
QScrollBar::handle:vertical { background: #3a3a4a; min-height: 24px; border-radius: 5px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: #1b1b22; height: 12px; }
QScrollBar::handle:horizontal { background: #3a3a4a; min-width: 24px; border-radius: 5px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
"""


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
