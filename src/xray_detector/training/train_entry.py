from __future__ import annotations

import argparse
import json
import traceback
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ultralytics traningsentry for xray-detector")
    parser.add_argument("--data", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--epochs", type=int, required=True)
    parser.add_argument("--imgsz", type=int, required=True)
    parser.add_argument("--batch", type=int, required=True)
    parser.add_argument("--lr", type=float, required=True)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--project", required=True)
    parser.add_argument("--name", default="train")
    parser.add_argument("--result", required=True)
    return parser.parse_args()


def resolve_device(requested: str) -> str:
    if requested.lower() != "auto":
        return requested
    try:
        import torch

        if torch.cuda.is_available():
            return "0"
    except Exception:
        pass
    return "cpu"


def main() -> int:
    args = parse_args()
    result_path = Path(args.result)
    try:
        from ultralytics import YOLO

        model = YOLO(args.model)
        results = model.train(
            data=args.data,
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            lr0=args.lr,
            device=resolve_device(args.device),
            workers=args.workers,
            seed=args.seed,
            project=args.project,
            name=args.name,
            exist_ok=True,
            verbose=True,
        )
        best = ""
        trainer = getattr(model, "trainer", None)
        if trainer is not None and getattr(trainer, "best", None):
            best = str(trainer.best)
        if not best:
            candidate = Path(args.project) / args.name / "weights" / "best.pt"
            if candidate.exists():
                best = str(candidate)
        metrics = {}
        results_dict = getattr(results, "results_dict", None)
        if isinstance(results_dict, dict):
            metrics = {str(key): _plain(value) for key, value in results_dict.items()}
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps({"best": best, "metrics": metrics}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"DONE {best}")
        return 0
    except Exception as exc:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(
                {"error": str(exc), "traceback": traceback.format_exc()},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        traceback.print_exc()
        return 1


def _plain(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
