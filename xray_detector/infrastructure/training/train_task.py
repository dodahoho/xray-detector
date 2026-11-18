import argparse
import csv
import inspect
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from json import load as json_load
from pathlib import Path

from xray_detector.domain.training import default_batch, rfdetr_resolution_error
from xray_detector.infrastructure.dataset_store.json_io import atomic_write_json
from xray_detector.infrastructure.dataset_store.yolo import read_classes
from xray_detector.infrastructure.detectors.yolo_detector import resolve_device
from xray_detector.infrastructure.training.epoch_metrics import (
    EpochReporter,
    abort_line,
)
from xray_detector.infrastructure.training.progress import ProgressReporter

MANIFEST_NAME = "training_manifest.json"
YOLO_RUN_DIR = "yolo"
RFDETR_RUN_DIR = "rfdetr"

#: Dataloader-arbetare för RF-DETR. Paketets default är 2, vilket svälter GPU:n
#: på ett stort dataset (TASK-91).
DEFAULT_WORKERS = 8
#: Träningens seed, så en körning går att göra om (TASK-91, TASK-92).
DEFAULT_SEED = 42
#: Epoker utan förbättrat valvärde innan ramverkets early stopping stoppar
#: träningen (TASK-118).
DEFAULT_PATIENCE = 10

#: YOLO:ts hyperparametrar för röntgenbilder (TASK-92).
#:
#: Ultralytics default passar dåligt här: ``optimizer=auto`` väljer SGD eller
#: AdamW utifrån epokantalet, så samma konfiguration kan ge olika optimerare;
#: ``degrees=0`` tillåter ingen rotation trots att objekten ligger på godtycklig
#: ledd; ``mosaic=1.0`` limmar ihop fyra bilder till scener som inte finns på
#: riktigt; och ``hsv_s=0.7`` ändrar mättnaden kraftigt i en nästan gråskalig
#: bild. Värdena skrivs också i manifestet, så en genomförd körning går att
#: läsa av efteråt.
YOLO_HYPERPARAMETERS = {
    "optimizer": "AdamW",
    "lr0": 0.001,
    "cos_lr": True,
    "seed": DEFAULT_SEED,
    "deterministic": True,
    "mosaic": 0.3,
    "close_mosaic": 15,
    "degrees": 30,
    "translate": 0.1,
    "scale": 0.5,
    "fliplr": 0.5,
    "flipud": 0.0,
    "hsv_h": 0.015,
    "hsv_s": 0.2,
    "hsv_v": 0.4,
}

#: RF-DETR:s bästa checkpoints i den ordning de föredras. checkpoint_best_total
#: skrivs först när träningen är klar, så under en pågående eller avbruten
#: körning är ema/regular det bästa som finns. last_ema.pth är slutvikterna och
#: står medvetet inte med.
RFDETR_BEST_CHECKPOINTS = (
    "checkpoint_best_total.pth",
    "checkpoint_best_ema.pth",
    "checkpoint_best_regular.pth",
)


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
    # samma läsare som datasetvyn, så manifestet och vyn alltid är överens
    return read_classes(dataset)


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
    #: "overfitting" när ramverkets early stopping stoppade körningen, "error"
    #: vid ett undantag (TASK-97). Skillnaden avgör om körningen gick bra eller
    #: kraschade.
    stop_reason: str | None = None
    metrics: dict[str, float] = field(default_factory=dict)
    epochs_completed: int = 0


@dataclass
class TrainArgs:
    """Träningens indata (TASK-146).

    Byggs ur argparse i main() och direkt i testerna, så ingen kod muterar en
    argparse.Namespace efter parsningen.
    """

    dataset: str
    weights: str
    output: str = ""
    epochs: int = 100
    imgsz: int = 640
    batch: int | None = None
    device: str = "cuda"
    family: str = "yolo"
    workers: int = DEFAULT_WORKERS
    seed: int = DEFAULT_SEED
    overfitting_guard: str = "on"
    overfitting_patience: int = DEFAULT_PATIENCE
    name: str = ""
    base_name: str = ""
    #: sätts i main(): absolut körningskatalog respektive starttid
    output_path: Path | None = None
    started: datetime | None = None


def _output_path(value: str) -> Path:
    """Absolut körningskatalog (TASK-47).

    Ultralytics lägger relativa project-sökvägar under runs/detect/, så en
    relativ --output skulle ge en annan snapshot-katalog än en absolut.
    """
    return Path(value).resolve()


def _prepare_run_dir(args: TrainArgs) -> Path:
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

    RF-DETR skriver checkpoint_best_total.pth först när träningen är klar och
    last_ema.pth löpande. Den senare är slutvikterna, inte de bästa, så valet
    är explicit i stället för att ta den senast ändrade filen.
    """
    if family == "rfdetr":
        candidates = [
            run_dir / RFDETR_RUN_DIR / name for name in RFDETR_BEST_CHECKPOINTS
        ]
    else:
        candidates = [run_dir / YOLO_RUN_DIR / "weights" / "best.pt"]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _hyperparameters(args: TrainArgs) -> dict:
    """Hyperparametrarna som skickas till ramverket, för manifestet (TASK-92).

    YOLO:s värden är desamma som ``_train_yolo`` skickar, så manifestet visar
    vad körningen faktiskt använde i stället för vad ultralytics råkade
    defaulta till.
    """
    if args.family == "rfdetr":
        return {
            "resolution": args.imgsz,
            "num_workers": args.workers,
            "seed": args.seed,
        }
    return dict(YOLO_HYPERPARAMETERS)


def _write_manifest(args: TrainArgs, run_dir: Path, state: _RunState) -> None:
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
    started = args.started
    finished = None if state.status == "running" else datetime.now(UTC)
    manifest = {
        "family": args.family,
        # visningsnamnet byggs av GUI:t, som känner datasetets sammansättning
        # och basmodellens namn (TASK-108)
        "name": args.name or None,
        "base_model_name": args.base_name or None,
        "base_weights": args.weights,
        "weights_relative": best.relative_to(run_dir).as_posix(),
        "classes": _read_data_classes(Path(args.dataset)),
        "dataset_yaml": str(args.dataset),
        "epochs": args.epochs,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "device": args.device,
        "hyperparameters": _hyperparameters(args),
        "overfitting_guard": args.overfitting_guard == "on",
        "metrics": metrics,
        "epochs_completed": state.epochs_completed,
        "status": state.status,
        "abort_reason": state.reason,
        "stop_reason": state.stop_reason,
        "started": started.isoformat() if started is not None else None,
        "finished": finished.isoformat() if finished is not None else None,
        "duration_seconds": (
            round((finished - started).total_seconds(), 1)
            if finished is not None and started is not None
            else None
        ),
        "date": datetime.now(UTC).isoformat(),
    }
    atomic_write_json(run_dir / MANIFEST_NAME, manifest)


def _metrics_path(args: TrainArgs, run_dir: Path) -> Path:
    if args.family == "rfdetr":
        return run_dir / RFDETR_RUN_DIR / "metrics.csv"
    return run_dir / YOLO_RUN_DIR / "results.csv"


def _start_reporter(args: TrainArgs, run_dir: Path, state: _RunState):
    """Startar epokrapportören som skickar EPOCH-rader och håller manifestet färskt."""

    def on_epoch(metrics) -> None:
        state.metrics = metrics.as_dict()
        state.epochs_completed = metrics.epoch
        _write_manifest(args, run_dir, state)

    reporter = EpochReporter(
        _metrics_path(args, run_dir), args.family, args.epochs, on_epoch
    )
    reporter.start()
    return reporter


def _stopped_early(args: TrainArgs, state: _RunState) -> bool:
    """Sant när ramverkets early stopping avslutade körningen i förtid (TASK-118).

    Ultralytics och rfdetr stoppar båda själva när valvärdet stått still, så
    det syns bara som att färre epoker blev klara än vad som begärdes.
    """
    return args.overfitting_guard == "on" and 0 < state.epochs_completed < args.epochs


def _early_stop_reason(args: TrainArgs, state: _RunState) -> str:
    """Orsaken som visas i träningsvyn och sparas i manifestet (TASK-118)."""
    return (
        f"Tidigt stopp: valvärdet förbättrades inte under de senaste "
        f"{args.overfitting_patience} epokerna (epok {state.epochs_completed} "
        f"av {args.epochs})"
    )


def _finish_state(args: TrainArgs, state: _RunState) -> None:
    """Avgör hur körningen slutade innan manifestet skrivs (TASK-97, TASK-118).

    Ett tidigt stopp av ramverkets early stopping är ett lyckat utfall och
    sparas därför som ``overfitting``, medan ett undantag redan har satt
    ``error``. Skillnaden låter historikvyn skilja ett planerat stopp från en
    krasch.
    """
    if state.status != "running":
        return
    if _stopped_early(args, state):
        state.status = "aborted"
        state.reason = _early_stop_reason(args, state)
        state.stop_reason = "overfitting"
    else:
        state.status = "completed"


def _use_utf8_output() -> None:
    """Kopplar om stdout och stderr till UTF-8 (TASK-113).

    rfdetr ritar tabeller med rich, som använder box-tecken som cp1252 inte kan
    koda: med stdout kopplad till en pipe kraschade träningen på
    UnicodeEncodeError. GUI:t läser dessutom processens stdout som UTF-8, så
    teckenkodningen måste vara densamma oavsett vilken konsol processen fick —
    annars blir svenska tecken i träningsloggen mojibake.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            continue


def main() -> None:
    _use_utf8_output()
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="Sökväg till YOLO data.yaml")
    parser.add_argument("--weights", required=True, help="Basmodell")
    parser.add_argument("--output", required=True, help="Katalog för sparade vikter")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument(
        "--batch",
        type=int,
        default=None,
        help="Bilder per steg; familjens default när det inte anges",
    )
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--family", default="yolo", choices=["yolo", "rfdetr"])
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help="Dataloader-arbetare (RF-DETR)",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--overfitting-guard",
        default="on",
        choices=["on", "off"],
        help="Stoppa träningen med ramverkets early stopping när valvärdet stannar",
    )
    parser.add_argument(
        "--overfitting-patience",
        type=int,
        default=DEFAULT_PATIENCE,
        help="Epoker utan förbättrat valvärde innan träningen stoppas",
    )
    parser.add_argument(
        "--name",
        default="",
        help="Visningsnamn för den tränade modellen (TASK-108)",
    )
    parser.add_argument(
        "--base-name",
        default="",
        help="Basmodellens visningsnamn, ärvt vid vidareträning (TASK-108)",
    )
    args = TrainArgs(**vars(parser.parse_args()))
    if args.batch is None:
        args.batch = default_batch(args.family)
    if args.family == "rfdetr":
        # avvisas innan körningskatalogen skapas, så ett fel inte lämnar en
        # halvstartad körning efter sig (TASK-91)
        error = rfdetr_resolution_error(args.imgsz)
        if error is not None:
            print(f"Fel: {error}", file=sys.stderr, flush=True)
            raise SystemExit(2)
    args.output_path = _output_path(args.output)
    args.started = datetime.now(UTC)

    device = resolve_device(args.device)
    print(f"Träning på enhet: {device}")
    run_dir = _prepare_run_dir(args)
    args.output_path = run_dir
    print(f"Körningskatalog: {run_dir}")
    state = _RunState()
    reporter = _start_reporter(args, run_dir, state)
    progress = ProgressReporter()
    try:
        if args.family == "rfdetr":
            _train_rfdetr(args, device)
        else:
            _train_yolo(args, device, progress)
    except BaseException as exc:
        state.status = "aborted"
        state.reason = str(exc) or type(exc).__name__
        state.stop_reason = "error"
        raise
    finally:
        reporter.stop()
        reporter.join(timeout=5)
        _finish_state(args, state)
        if state.stop_reason == "overfitting" and state.reason is not None:
            print(abort_line(state.reason), flush=True)
        _write_manifest(args, run_dir, state)
    print("TRAINING_DONE")


def _train_yolo(args: TrainArgs, device, progress: ProgressReporter) -> Path:
    # ultralytics är tungt och valfritt, så det importeras först vid träningen
    from ultralytics import YOLO  # noqa: PLC0415

    model = YOLO(args.weights)
    model.add_callback("on_train_batch_end", _batch_callback(progress))
    model.train(
        data=args.dataset,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=device,
        project=args.output_path,
        name=YOLO_RUN_DIR,
        exist_ok=True,
        # ultralytics egen early stopping; 0 stänger av den (TASK-118)
        patience=args.overfitting_patience if args.overfitting_guard == "on" else 0,
        **YOLO_HYPERPARAMETERS,
    )
    return args.output_path / YOLO_RUN_DIR


def _batch_callback(progress: ProgressReporter):
    """Rapporterar hur långt epoken kommit, throttlat av rapportören (TASK-96).

    Ultralytics saknar ett epokevent mitt i epoken, men varje avslutad batch
    går genom on_train_batch_end. Antalet steg läses ur träningslastaren en
    gång per epok, så andelen går att räkna ut.
    """

    state = {"epoch": None, "step": 0, "total_steps": 0}

    def on_train_batch_end(trainer) -> None:
        epoch = int(getattr(trainer, "epoch", 0)) + 1
        if state["epoch"] != epoch:
            state["epoch"] = epoch
            state["step"] = 0
            loader = getattr(trainer, "train_loader", None)
            state["total_steps"] = len(loader) if loader is not None else 0
        state["step"] += 1
        total = state["total_steps"]
        if not total:
            return
        progress.update(epoch, state["step"], total, force=state["step"] >= total)

    return on_train_batch_end


def _train_rfdetr(args: TrainArgs, device) -> Path:
    """Trainer vald RF-DETR-modell pa exporterat rfdetr-dataset.

    Basmodellen ar antingen en publicerad storlek eller en egen snapshot
    (TASK-107). rfdetr-paketet ar valfritt och dess train()-signatur varierar
    mellan versioner: kwargs filtreras därför mot den faktiska signaturen.

    Upplösningen sätts vid konstruktionen för en storlek och skickas dessutom
    till train(), som räknar om positionskodningarna när den ändras. En
    snapshot bär sin egen upplösning i model_config och får vyns värde först
    där (TASK-91, TASK-107). num_workers och seed sätts explicit: paketet
    defaultar till 2 arbetare, vilket svälter GPU:n på ett stort dataset, och
    till ingen seed alls, vilket gör körningen omöjlig att göra om.
    early_stopping är paketets egen mekanism (TASK-118).
    """
    # rfdetr är ett valfritt extra, så det importeras först vid träningen
    from xray_detector.infrastructure.detectors.rfdetr_detector import (  # noqa: PLC0415
        load_rfdetr_model,
    )

    model = load_rfdetr_model(args.weights, args.imgsz)
    self = model.train
    params = inspect.signature(self).parameters
    wanted = {
        "dataset_dir": args.dataset,
        "epochs": args.epochs,
        "batch_size": args.batch,
        "device": device,
        "num_workers": args.workers,
        "seed": args.seed,
        "resolution": args.imgsz,
        "early_stopping": args.overfitting_guard == "on",
        "early_stopping_patience": args.overfitting_patience,
    }
    kwargs = {k: v for k, v in wanted.items() if k in params or _varkw(params)}
    run_dir = args.output_path / RFDETR_RUN_DIR
    kwargs.setdefault("output_dir", str(run_dir))
    self(**kwargs)
    return run_dir


def _varkw(params) -> bool:
    return any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())


if __name__ == "__main__":
    main()
