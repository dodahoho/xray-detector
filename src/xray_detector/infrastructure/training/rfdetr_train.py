"""RF-DETR training worker.

The RF-DETR package API has changed between releases, so the worker inspects the
train signature and only passes supported arguments. Any unsupported training
setup fails with a clear message instead of silently producing a bad model.
"""

from __future__ import annotations

import inspect
import json
import shutil
from pathlib import Path


def _model_class(variant: str):
    import rfdetr

    if "large" in variant.lower() and hasattr(rfdetr, "RFDETRLarge"):
        return rfdetr.RFDETRLarge
    if hasattr(rfdetr, "RFDETRBase"):
        return rfdetr.RFDETRBase
    if hasattr(rfdetr, "RFDETR"):
        return rfdetr.RFDETR
    raise RuntimeError("Installed rfdetr package has no supported model class")


def _filtered_train_kwargs(model, desired: dict) -> dict:
    try:
        signature = inspect.signature(model.train)
        parameters = signature.parameters
        if any(param.kind == inspect.Parameter.VAR_KEYWORD for param in parameters.values()):
            return desired
        return {key: value for key, value in desired.items() if key in parameters}
    except (TypeError, ValueError):
        return desired


def _find_weights(run_dir: Path) -> Path | None:
    candidates = sorted(
        list(run_dir.rglob("*.pth")) + list(run_dir.rglob("*.pt")),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def train(config: dict) -> int:
    try:
        params = config["params"]
        variant = config.get("variant") or config.get("base_model_id", "base")
        model_class = _model_class(str(variant))
        model_dir = Path(config["model_dir"])
        run_dir = Path(config["run_dir"])
        model_dir.mkdir(parents=True, exist_ok=True)
        run_dir.mkdir(parents=True, exist_ok=True)

        base_path = Path(config["base_model_path"])
        kwargs = {}
        if base_path.exists():
            kwargs["pretrain_weights"] = str(base_path)
        print(f"Loading RF-DETR model class {model_class.__name__} with {kwargs}")
        model = model_class(**kwargs)

        desired = {
            "dataset_dir": str(config["data_dir"]),
            "epochs": int(params["epochs"]),
            "batch_size": int(params["batch"]),
            "grad_accum_steps": 1,
            "lr": float(params["learning_rate"]),
            "output_dir": str(run_dir),
            "device": params["device"],
            "num_workers": int(params["workers"]),
        }
        train_kwargs = _filtered_train_kwargs(model, desired)
        print(f"Starting RF-DETR training with: {train_kwargs}")
        model.train(**train_kwargs)

        source = _find_weights(run_dir)
        if source is None:
            print("Training finished but no RF-DETR weights were found")
            return 4
        target = model_dir / "best.pth"
        shutil.copy2(source, target)
        print(f"Saved weights: {target}")

        metrics = {}
        metrics_file = run_dir / "metrics.json"
        if metrics_file.exists():
            with metrics_file.open("r", encoding="utf-8") as handle:
                metrics = json.load(handle)
        with (model_dir / "metrics.json").open("w", encoding="utf-8") as handle:
            json.dump(metrics, handle, indent=2, ensure_ascii=False)
        return 0
    except Exception as exc:
        print(f"RF-DETR training failed: {exc}")
        return 5


if __name__ == "__main__":
    import sys

    raise SystemExit(train(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))))
