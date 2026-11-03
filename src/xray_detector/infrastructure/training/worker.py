"""Training worker entry point.

Run in a separate process so that training failures cannot take down the UI.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("Usage: python -m xray_detector.infrastructure.training.worker <config.json>")
        return 2
    config_path = Path(args[0])
    with config_path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)

    family = config["family"].lower()
    if family == "yolo":
        from xray_detector.infrastructure.training.yolo_train import train

        return train(config)
    if family == "rfdetr":
        from xray_detector.infrastructure.training.rfdetr_train import train

        return train(config)
    print(f"Unsupported model family: {family}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
