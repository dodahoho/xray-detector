"""Entry point för xray-detector.

Kör:
    python main.py
    python main.py --config path/to/config.yaml
    python main.py --no-fullscreen
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from loguru import logger

from PySide6.QtWidgets import QApplication

from xray_detector.config import load_config
from xray_detector.app import MainWindow


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="X-ray detector")
    p.add_argument("--config", type=Path, default=None,
                   help="Path till config.yaml")
    p.add_argument("--no-fullscreen", action="store_true",
                   help="Starta i vanligt fönster")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    if args.no_fullscreen:
        config.app.fullscreen = False

    # Loggning
    logger.remove()
    logger.add(sys.stderr, level="INFO",
               format="{time:HH:mm:ss} | {level: <8} | {message}")
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    logger.add(str(log_dir / "xray_{time:YYYYMMDD}.log"), level="DEBUG",
               rotation="1 day", retention="7 days", encoding="utf-8")

    app = QApplication(sys.argv)
    app.setApplicationName("X-ray Detector")

    window = MainWindow(config)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
