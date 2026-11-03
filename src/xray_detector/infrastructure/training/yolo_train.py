"""YOLO training worker."""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path


def _copy_weights(source_dir: Path, model_dir: Path) -> dict[str, str]:
    weights: dict[str, str] = {}
    for name in ("best.pt", "last.pt"):
        source = source_dir / name
        if source.exists():
            target = model_dir / name
            shutil.copy2(source, target)
            weights[name.split(".")[0]] = str(target)
    return weights


def _read_metrics(results_csv: Path) -> dict:
    if not results_csv.exists():
        return {}
    try:
        with results_csv.open("r", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            return {}
        last = rows[-1]
        return {key: _to_number(value) for key, value in last.items()}
    except Exception:
        return {}


def _to_number(value: str):
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def train(config: dict) -> int:
    try:
        from ultralytics import YOLO
    except Exception as exc:
        print(f"Ultralytics is not available: {exc}")
        return 3

    params = config["params"]
    model_dir = Path(config["model_dir"])
    run_dir = Path(config["run_dir"])
    model_dir.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading base model: {config['base_model_path']}")
    model = YOLO(config["base_model_path"])
    train_args = {
        "data": config["data_yaml"],
        "epochs": int(params["epochs"]),
        "batch": int(params["batch"]),
        "imgsz": int(params["imgsz"]),
        "lr0": float(params["learning_rate"]),
        "patience": int(params["patience"]),
        "workers": int(params["workers"]),
        "device": params["device"],
        "project": str(run_dir),
        "name": "ultralytics",
        "exist_ok": True,
        "verbose": True,
    }
    print(f"Starting YOLO training with: {train_args}")
    model.train(**train_args)

    weights_dir = run_dir / "ultralytics" / "weights"
    weights = _copy_weights(weights_dir, model_dir)
    metrics = _read_metrics(run_dir / "ultralytics" / "results.csv")
    with (model_dir / "metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2, ensure_ascii=False)
    if not weights:
        print("Training finished but no weights were found")
        return 4
    print(f"Saved weights: {weights}")
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(train(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))))
