"""Tidigare träningar och export av deras modeller (TASK-59).

Varje träningskörning beskrivs av sitt ``training_manifest.json`` under
``models/trained/``. Modulen läser dem till :class:`TrainingRun` och kopierar
en vald körnings vikter och manifest till en katalog användaren väljer.
"""

import shutil
from dataclasses import dataclass
from datetime import datetime
from json import load as json_load
from pathlib import Path

from xray_detector.domain.training import EpochMetrics
from xray_detector.infrastructure.training.epoch_metrics import read_epoch_history

MANIFEST_NAME = "training_manifest.json"
#: Metrics-filen träningsprocessen skriver per familj (TASK-70).
METRICS_FILES = {
    "yolo": ("yolo", "results.csv"),
    "rfdetr": ("rfdetr", "metrics.csv"),
}
STATUS_LABELS = {
    "completed": "Klar",
    "aborted": "Avbruten",
    "running": "Pågår",
}
UNKNOWN = "-"


@dataclass(frozen=True)
class TrainingRun:
    """En genomförd träningskörning ur sitt manifest."""

    run_id: str
    run_dir: Path
    family: str
    base_weights: str
    weights: Path
    epochs: int
    epochs_completed: int
    status: str
    started: str | None
    finished: str | None
    duration_seconds: float | None
    metrics: dict
    classes: list[str]
    dataset_yaml: str
    imgsz: int | None
    batch: int | None

    @property
    def status_label(self) -> str:
        return STATUS_LABELS.get(self.status, self.status or UNKNOWN)

    @property
    def duration_text(self) -> str:
        seconds = self.duration_seconds
        if seconds is None:
            return UNKNOWN
        minutes, rest = divmod(round(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours} h {minutes} min"
        if minutes:
            return f"{minutes} min {rest} s"
        return f"{rest} s"

    @property
    def epochs_text(self) -> str:
        if self.epochs_completed and self.epochs_completed != self.epochs:
            return f"{self.epochs_completed}/{self.epochs}"
        return str(self.epochs)

    @property
    def map50_95_text(self) -> str:
        value = self.metrics.get("map50_95")
        return UNKNOWN if value is None else f"{float(value):.3f}"

    @property
    def details(self) -> str:
        """Viktiga parametrar för vald körning."""
        parts = [
            f"Familj: {self.family}",
            f"Basmodell: {Path(self.base_weights).stem}",
            f"Dataset: {self.dataset_yaml}",
            f"Bildstorlek: {self.imgsz if self.imgsz is not None else UNKNOWN}",
            f"Batch: {self.batch if self.batch is not None else UNKNOWN}",
            f"Epoker: {self.epochs_text}",
            f"mAP50-95: {self.map50_95_text}",
            f"Status: {self.status_label}",
        ]
        if self.classes:
            parts.append(f"Klasser: {', '.join(self.classes)}")
        return "  ·  ".join(parts)


def training_runs(trained_dir: Path) -> list[TrainingRun]:
    """Alla träningskörningar under katalogen, nyast först."""
    trained_dir = Path(trained_dir)
    runs = []
    for manifest_path in trained_dir.rglob(MANIFEST_NAME):
        run = _read_run(trained_dir, manifest_path)
        if run is not None:
            runs.append(run)
    return sorted(runs, key=_sort_key, reverse=True)


def _read_run(trained_dir: Path, manifest_path: Path) -> TrainingRun | None:
    try:
        with open(manifest_path, encoding="utf-8") as file:
            manifest = json_load(file)
        weights = manifest_path.parent / manifest.get("weights_relative", "")
        if not weights.is_file():
            return None
        run_dir = manifest_path.parent
        run_id = run_dir.relative_to(trained_dir).as_posix()
    except (OSError, ValueError):
        return None
    started = manifest.get("started") or manifest.get("date")
    finished = manifest.get("finished")
    return TrainingRun(
        run_id=run_id,
        run_dir=run_dir,
        family=str(manifest.get("family") or "yolo"),
        base_weights=str(manifest.get("base_weights") or ""),
        weights=weights,
        epochs=int(manifest.get("epochs") or 0),
        epochs_completed=int(manifest.get("epochs_completed") or 0),
        status=str(manifest.get("status") or "completed"),
        started=started,
        finished=finished,
        duration_seconds=_duration(manifest, started, finished),
        metrics=dict(manifest.get("metrics") or {}),
        classes=[str(name) for name in manifest.get("classes") or []],
        dataset_yaml=str(manifest.get("dataset_yaml") or ""),
        imgsz=manifest.get("imgsz"),
        batch=manifest.get("batch"),
    )


def _duration(manifest: dict, started, finished) -> float | None:
    value = manifest.get("duration_seconds")
    if isinstance(value, (int, float)):
        return float(value)
    if not started or not finished:
        return None
    try:
        return (datetime.fromisoformat(finished) - datetime.fromisoformat(started)).total_seconds()
    except (TypeError, ValueError):
        return None


def _sort_key(run: TrainingRun) -> tuple[str, str]:
    """Nyast först; manifest utan tidsstämpel sorteras på körningsnamnet."""
    return (run.started or "", run.run_id)


def run_epochs(run: TrainingRun) -> list[EpochMetrics]:
    """Körningens sparade epokvärden ur metrics-filen (TASK-70).

    Manifestet sparar bara sista epokens värden, så grafen läses ur filen som
    träningsprocessen skrev. Saknas filen blir listan tom.
    """
    folder, name = METRICS_FILES.get(run.family, METRICS_FILES["yolo"])
    return read_epoch_history(run.run_dir / folder / name, run.family, run.epochs)


def export_run(run: TrainingRun, target_dir: Path) -> Path:
    """Kopierar vikterna och manifestet till target_dir/<körning>/.

    Vikterna behåller sitt format (.pt för YOLO, .pth för RF-DETR), vilket är
    det format både appen och ultralytics/rfdetr läser. Manifestet följer med
    så modellen är självbeskrivande utanför appen.
    """
    target = Path(target_dir) / run.run_id.replace("/", "_")
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(run.weights, target / run.weights.name)
    manifest = run.run_dir / MANIFEST_NAME
    if manifest.is_file():
        shutil.copy2(manifest, target / MANIFEST_NAME)
    return target
