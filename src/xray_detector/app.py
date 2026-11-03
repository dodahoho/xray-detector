"""Application factory."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from xray_detector.config import AppConfig, user_config_path
from xray_detector.logging_setup import configure_logging
from xray_detector.ui.theme import apply_theme


def create_application(
    argv: list[str] | None = None,
    config_path: str | None = None,
) -> tuple[QApplication, AppConfig]:
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("X-ray detector")
    app.setOrganizationName("XrayDetector")
    app.setApplicationVersion("0.1.0")

    from pathlib import Path

    path = Path(config_path) if config_path else user_config_path()
    config = AppConfig.load(path)
    config.ensure_dirs()
    configure_logging(config.logs_dir, config.app.log_level)
    apply_theme(app)
    return app, config
