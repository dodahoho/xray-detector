"""Command line entry point."""

from __future__ import annotations

import argparse
import sys

from xray_detector.app import create_application
from xray_detector.ui.main_window import MainWindow


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="X-ray detector")
    parser.add_argument("--config", help="Path to an alternative config file")
    parser.add_argument("--kiosk", action="store_true", help="Start in kiosk mode")
    args, qt_args = parser.parse_known_args(argv)

    app, config = create_application([sys.argv[0], *qt_args], config_path=args.config)
    if args.kiosk:
        config.ui.kiosk = True
        config.ui.fullscreen = True
    window = MainWindow(config)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
