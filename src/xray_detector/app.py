from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from xray_detector.config import load_config
from xray_detector.dataset.store import get_or_create_store
from xray_detector.ui.main_window import MainWindow
from xray_detector.util.logging import setup_logging
from xray_detector.util.paths import AppPaths

LOGGER = logging.getLogger(__name__)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="X-ray detector")
    parser.add_argument("--config", type=Path, default=None, help="Sökväg till TOML-konfiguration")
    parser.add_argument("--data-dir", type=Path, default=None, help="Katalog för dataset och modeller")
    parser.add_argument("--verbose", action="store_true", help="Debug-loggning")
    return parser.parse_args(argv[1:])


def run(argv: list[str]) -> int:
    args = _parse_args(argv)
    try:
        config = load_config(args.config)
    except Exception as exc:
        print(f"Kunde inte läsa konfigurationen: {exc}", file=sys.stderr)
        return 2
    if args.data_dir is not None:
        config.app.data_dir = str(args.data_dir)

    paths = AppPaths.from_config(config).ensure()
    setup_logging(paths.logs, verbose=args.verbose)
    LOGGER.info("Startar X-ray detector")

    app = QApplication(argv)
    app.setApplicationName("X-ray detector")
    app.setOrganizationName("X-ray detector")

    def handle_exception(exc_type, exc_value, exc_traceback):  # type: ignore[no-untyped-def]
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        LOGGER.critical("Ohanterat fel", exc_info=(exc_type, exc_value, exc_traceback))
        QMessageBox.critical(
            None,
            "Oväntat fel",
            f"Ett oväntat fel inträffade:\n{exc_value}\n\nSe loggen i {paths.logs}",
        )

    sys.excepthook = handle_exception
    try:
        get_or_create_store(paths.datasets, config.app.active_dataset)
        window = MainWindow(config, paths)
    except Exception as exc:
        LOGGER.exception("Kunde inte starta applikationen")
        QMessageBox.critical(None, "Startfel", f"Kunde inte starta applikationen:\n{exc}")
        return 1

    window.show()
    if config.app.fullscreen or config.app.kiosk:
        window.showFullScreen()
    return app.exec()
