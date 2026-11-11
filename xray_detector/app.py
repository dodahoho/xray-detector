import sys
from pathlib import Path

from xray_detector.application.app_config import load_config_with_yaml, setup_logging
from xray_detector.ui.main_window import MainWindow

ICON_PATH = Path(__file__).parent / "ui" / "assets" / "app.ico"


def _install_message_filter() -> None:
    from PySide6.QtCore import qInstallMessageHandler

    def handler(mode, context, message) -> None:
        if "CreateFontFaceFromHDC() failed" in message:
            return
        print(message, file=sys.stderr)

    qInstallMessageHandler(handler)


def _set_app_user_model_id() -> None:
    """Ger processen en egen identitet i aktivitetsfältet.

    Utan den grupperar Windows fönstret under python.exe och visar
    Python-ikonen när det fästs, oavsett vilken ikon Qt sätter.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("xray-detector")
    except Exception:
        pass


def main() -> int:
    _install_message_filter()
    _set_app_user_model_id()
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(ICON_PATH)))
    from xray_detector.ui.crash_dialog import install_exception_dialog

    install_exception_dialog()
    app.setApplicationName("X-ray detector")
    config, config_file = load_config_with_yaml(config_dir=None, workdir=Path.cwd())
    config.ensure_dirs()
    log = setup_logging(config.data_dir)
    log.info("Startar X-ray detector (konfig: %s)", config_file or "default")
    window = MainWindow(config)
    window.show_window()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
