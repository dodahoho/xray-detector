import sys

from PySide6.QtWidgets import QApplication

from xray_detector.config import load_config
from xray_detector.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("X-ray detector")
    config = load_config()
    window = MainWindow(config)
    window.showFullScreen()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
