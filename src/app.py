from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication

from src.core.config import AppConfig
from src.ui.main_window import MainWindow


def run_app(config_path: str = "config.yaml") -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("X-ray Detector")
    config = AppConfig(config_path=config_path)
    window = MainWindow(config=config)
    app.installEventFilter(window._activity_filter)
    if not window.isFullScreen():
        window.show()
    return app.exec()
