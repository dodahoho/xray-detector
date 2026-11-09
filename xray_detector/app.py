import sys

from xray_detector.domain.config import load_config
from xray_detector.ui.main_window import MainWindow


def _install_message_filter() -> None:
    from PySide6.QtCore import qInstallMessageHandler

    def handler(mode, context, message) -> None:
        if "CreateFontFaceFromHDC() failed" in message:
            return
        print(message, file=sys.stderr)

    qInstallMessageHandler(handler)


def main() -> int:
    _install_message_filter()
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setApplicationName("X-ray detector")
    config = load_config()
    window = MainWindow(config)
    window.show_window()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
