import argparse
import ast
import csv
import json
from datetime import UTC, datetime
from json import load as json_load
from pathlib import Path


def _read_data_classes(dataset: Path) -> list[str]:
    """Klassnamn ur data.yaml (YOLO) eller _annotations.coco.json (RF-DETR)."""
    dataset = Path(dataset)
    if dataset.is_dir():
        coco_json = dataset / "train" / "_annotations.coco.json"
        try:
            with open(coco_json, encoding="utf-8") as file:
                categories = json_load(file).get("categories", [])
            return [str(category["name"]) for category in categories]
        except (OSError, ValueError):
            return []
    try:
        for line in dataset.read_text(encoding="utf-8").splitlines():
            if line.startswith("names:"):
                names = ast.literal_eval(line.removeprefix("names:").strip())
                if isinstance(names, dict):
                    names = [names[key] for key in sorted(names)]
                return [str(name) for name in names]
    except (OSError, ValueError, SyntaxError):
        pass
    return []


def _read_metrics(results_csv: Path) -> dict[str, float]:
    metrics: dict[str, float] = {}
    try:
        with open(results_csv, encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        if not rows:
            return metrics
        last = rows[-1]
        for column, value in last.items():
            if column is None or not column.startswith("metrics/"):
                continue
            try:
                metrics[column.removeprefix("metrics/")] = float(value)
            except (TypeError, ValueError):
                continue
    except OSError:
        pass
    return metrics


def _write_manifest(args, run_dir: Path) -> None:
    best = run_dir / "weights" / "best.pt"
    if not best.exists():
        candidates = sorted(run_dir.rglob("*.pth"), key=lambda p: p.stat().st_mtime)
        if not candidates:
            return
        best = candidates[-1]
    manifest = {
        "base_weights": args.weights,
        "weights_relative": best.relative_to(args.output_path).as_posix(),
        "classes": _read_data_classes(Path(args.dataset)),
        "dataset_yaml": str(args.dataset),
        "epochs": args.epochs,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "metrics": _read_metrics(run_dir / "results.csv"),
        "date": datetime.now(UTC).isoformat(),
    }
    manifest_path = args.output_path / "training_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as file:
        json.dump(manifest, file, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="Sökväg till YOLO data.yaml")
    parser.add_argument("--weights", required=True, help="Basmodell")
    parser.add_argument("--output", required=True, help="Katalog för sparade vikter")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--family", default="yolo", choices=["yolo", "rfdetr"])
    args = parser.parse_args()
    args.output_path = Path(args.output)

    from xray_detector.infrastructure.detectors.yolo_detector import resolve_device

    device = resolve_device(args.device)
    print(f"Träning på enhet: {device}")
    if args.family == "rfdetr":
        run_dir = _train_rfdetr(args, device)
    else:
        run_dir = _train_yolo(args, device)
    _write_manifest(args, run_dir)
    print("TRAINING_DONE")


def _train_yolo(args, device) -> Path:
    from ultralytics import YOLO

    model = YOLO(args.weights)
    model.train(
        data=args.dataset,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=device,
        project=args.output,
        name=f"{Path(args.weights).stem}",
        exist_ok=True,
    )
    return args.output_path / Path(args.weights).stem


def _train_rfdetr(args, device) -> Path:
    """Trainer RF-DETRBase pa exporterat rfdetr-dataset.

    rfdetr-paketet ar valfritt och dess train()-signatur varierar mellan
    versioner: kwargs filtreras därför mot den faktiska signaturen.
    """
    import inspect

    from rfdetr import RFDETRBase

    model = RFDETRBase()
    self = model.train
    params = inspect.signature(self).parameters
    wanted = {"dataset_dir": args.dataset, "epochs": args.epochs,
              "batch_size": args.batch, "device": device}
    kwargs = {k: v for k, v in wanted.items() if k in params or _varkw(params)}
    run_dir = args.output_path / "rfdetr"
    kwargs.setdefault("output_dir", str(run_dir))
    self(**kwargs)
    return run_dir


def _varkw(params) -> bool:
    return any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())


if __name__ == "__main__":
    main()
