import argparse
import ast
import csv
import inspect
from dataclasses import dataclass, field
from datetime import UTC, datetime
from json import load as json_load
from pathlib import Path

from xray_detector.infrastructure.training.epoch_metrics import (
    EpochReporter,
    abort_line,
)
from xray_detector.infrastructure.training.overfitting import (
    DEFAULT_PATIENCE,
    OverfittingGuard,
)

MANIFEST_NAME = "training_manifest.json"
YOLO_RUN_DIR = "yolo"
RFDETR_RUN_DIR = "rfdetr"


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
    """Sista radens numeriska värden, inklusive train- och val-loss (TASK-44).

    Används som reserv när epokeventen inte har fyllt på manifestets metrics.
    """
    metrics: dict[str, float] = {}
    try:
        with open(results_csv, encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        if not rows:
            return metrics
        for column, value in rows[-1].items():
            if column is None or column in ("epoch", "time", "step"):
                continue
            try:
                metrics[column.removeprefix("metrics/")] = float(value)
            except (TypeError, ValueError):
                continue
    except OSError:
        pass
    return metrics


@dataclass
class _RunState:
    """Det manifestet beskriver om körningen just nu (TASK-47)."""

    status: str = "running"
    reason: str | None = None
    metrics: dict[str, float] = field(default_factory=dict)
    epochs_completed: int = 0


@dataclass
class _StopSignal:
    """Delad flagga: rapportören sätter orsaken, träningsloopen läser den."""

    reason: str | None = None


def _prepare_run_dir(args) -> Path:
    """Unik körningskatalog; en ny körning skriver aldrig över en tidigare.

    GUI:t skickar en tidsstämplad katalog, men CLI:t kan peka på samma
    katalog två gånger. Då flyttas den nya körningen till <namn>_2 och framåt.
    """
    base = args.output_path
    if not (base / MANIFEST_NAME).exists():
        base.mkdir(parents=True, exist_ok=True)
        return base
    index = 2
    while True:
        candidate = base.with_name(f"{base.name}_{index}")
        if not (candidate / MANIFEST_NAME).exists():
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        index += 1


def _best_checkpoint(run_dir: Path, family: str) -> Path | None:
    """Bästa checkpoints för respektive familj (TASK-47).

    RF-DETR skriver både checkpoint_best_total.pth och last_ema.pth. Den
    senare är slutvikterna, inte de bästa, så valet är explicit i stället för
    att ta den senast ändrade filen.
    """
    if family == "rfdetr":
        candidate = run_dir / RFDETR_RUN_DIR / "checkpoint_best_total.pth"
    else:
        candidate = run_dir / YOLO_RUN_DIR / "weights" / "best.pt"
    return candidate if candidate.exists() else None


def _write_manifest(args, run_dir: Path, state: _RunState) -> None:
    """Skriver manifestet för körningen; anropas även under pågående träning.

    Manifestet skrivs om efter varje epok, så en avbruten eller hårdstoppad
    körning ändå har ett manifest som pekar på bästa hittillsvarande vikter.
    """
    best = _best_checkpoint(run_dir, args.family)
    if best is None:
        return
    metrics = dict(state.metrics)
    if not metrics:
        metrics = _read_metrics(run_dir / YOLO_RUN_DIR / "results.csv")
    started = getattr(args, "started", None)
    finished = None if state.status == "running" else datetime.now(UTC)
    manifest = {
        "family": args.family,
        "base_weights": args.weights,
        "weights_relative": best.relative_to(run_dir).as_posix(),
        "classes": _read_data_classes(Path(args.dataset)),
        "dataset_yaml": str(args.dataset),
        "epochs": args.epochs,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "device": args.device,
        "overfitting_guard": getattr(args, "overfitting_guard", "on") == "on",
        "metrics": metrics,
        "epochs_completed": state.epochs_completed,
        "status": state.status,
        "abort_reason": state.reason,
        "started": started.isoformat() if started is not None else None,
        "finished": finished.isoformat() if finished is not None else None,
        "duration_seconds": (
            round((finished - started).total_seconds(), 1)
            if finished is not None and started is not None
            else None
        ),
        "date": datetime.now(UTC).isoformat(),
    }
    from xray_detector.infrastructure.dataset_store.json_io import atomic_write_json

    atomic_write_json(run_dir / MANIFEST_NAME, manifest)


def _metrics_path(args, run_dir: Path) -> Path:
    if args.family == "rfdetr":
        return run_dir / RFDETR_RUN_DIR / "metrics.csv"
    return run_dir / YOLO_RUN_DIR / "results.csv"


def _start_reporter(args, run_dir: Path, state: _RunState, stop: _StopSignal):
    """Startar epokrapportören som skickar EPOCH-rader och håller manifestet färskt."""
    guard = (
        OverfittingGuard(args.overfitting_patience)
        if args.overfitting_guard == "on"
        else None
    )

    def on_epoch(metrics) -> None:
        if guard is not None and stop.reason is None:
            reason = guard.update(metrics)
            if reason is not None:
                stop.reason = reason
                print(abort_line(reason), flush=True)
        state.metrics = metrics.as_dict()
        state.epochs_completed = metrics.epoch
        _write_manifest(args, run_dir, state)

    reporter = EpochReporter(
        _metrics_path(args, run_dir), args.family, args.epochs, on_epoch
    )
    reporter.start()
    return reporter


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
    parser.add_argument(
        "--overfitting-guard",
        default="on",
        choices=["on", "off"],
        help="Avbryt träningen när överträning detekteras",
    )
    parser.add_argument("--overfitting-patience", type=int, default=DEFAULT_PATIENCE)
    args = parser.parse_args()
    # absolut sökväg: ultralytics lägger relativa project under runs/detect/ (TASK-47)
    args.output_path = Path(args.output).resolve()
    args.started = datetime.now(UTC)

    from xray_detector.infrastructure.detectors.yolo_detector import resolve_device

    device = resolve_device(args.device)
    print(f"Träning på enhet: {device}")
    run_dir = _prepare_run_dir(args)
    args.output_path = run_dir
    print(f"Körningskatalog: {run_dir}")
    state = _RunState()
    stop = _StopSignal()
    reporter = _start_reporter(args, run_dir, state, stop)
    try:
        if args.family == "rfdetr":
            _train_rfdetr(args, device)
        else:
            _train_yolo(args, device, stop)
    except BaseException as exc:
        state.status = "aborted"
        state.reason = str(exc) or type(exc).__name__
        raise
    finally:
        reporter.stop()
        reporter.join(timeout=5)
        if stop.reason is not None:
            state.status = "aborted"
            state.reason = stop.reason
        elif state.status == "running":
            state.status = "completed"
        _write_manifest(args, run_dir, state)
    print("TRAINING_DONE")


def _train_yolo(args, device, stop: _StopSignal) -> Path:
    from ultralytics import YOLO

    model = YOLO(args.weights)
    if args.overfitting_guard == "on":
        # on_fit_epoch_end körs efter save_metrics och save_model, så ett stop
        # här avbryter före nästa epok och bästa vikterna är redan sparade.
        model.add_callback("on_fit_epoch_end", lambda trainer: _apply_stop(trainer, stop))
    model.train(
        data=args.dataset,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=device,
        project=args.output_path,
        name=YOLO_RUN_DIR,
        exist_ok=True,
        patience=(
            args.overfitting_patience if args.overfitting_guard == "on" else args.epochs
        ),
    )
    return args.output_path / YOLO_RUN_DIR


def _apply_stop(trainer, stop: _StopSignal) -> None:
    """Stoppar ultralytics-träningen i träningsprocessen, inte från GUI:t."""
    if stop.reason is not None:
        trainer.stop = True


def _train_rfdetr(args, device) -> Path:
    """Trainer vald RF-DETR-storlek pa exporterat rfdetr-dataset.

    rfdetr-paketet ar valfritt och dess train()-signatur varierar mellan
    versioner: kwargs filtreras därför mot den faktiska signaturen.
    """
    from xray_detector.infrastructure.detectors.rfdetr_detector import rfdetr_variant

    model = rfdetr_variant(args.weights)()
    self = model.train
    params = inspect.signature(self).parameters
    wanted = {"dataset_dir": args.dataset, "epochs": args.epochs,
              "batch_size": args.batch, "device": device}
    if getattr(args, "overfitting_guard", "on") == "on":
        # RF-DETR saknar publik callback-krok, så avbrottet sker med paketets
        # egen early stopping: samma patience som vakten i rapportören.
        wanted["early_stopping"] = True
        wanted["early_stopping_patience"] = getattr(
            args, "overfitting_patience", DEFAULT_PATIENCE
        )
    kwargs = {k: v for k, v in wanted.items() if k in params or _varkw(params)}
    run_dir = args.output_path / RFDETR_RUN_DIR
    kwargs.setdefault("output_dir", str(run_dir))
    self(**kwargs)
    return run_dir


def _varkw(params) -> bool:
    return any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())


if __name__ == "__main__":
    main()
