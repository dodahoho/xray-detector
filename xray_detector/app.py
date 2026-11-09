import sys

from xray_detector.application.app_config import load_config_with_yaml, setup_logging
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
    config, config_file = load_config_with_yaml(config_dir=None, workdir=Path.cwd())
    config.ensure_dirs()
    log = setup_logging(config.data_dir)
    log.info("Startar X-ray detector (konfig: %s)", config_file or "default")
    window = MainWindow(config)
    window.show_window()
    return app.exec()


if __name__ == "__main__":
    from pathlib import Path

    sys.exit(main())
