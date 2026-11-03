from __future__ import annotations

import json
import re
import shutil
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from xray_detector.dataset.store import DatasetStore
from xray_detector.dataset.versioning import DatasetMetadata, utc_now_iso
from xray_detector.training.dataset_converter import YoloDatasetInfo, prepare_yolo_dataset
from xray_detector.training.manifest import ModelMetadata, write_model_metadata
from xray_detector.util.files import atomic_write_json, read_json

_SAFE = re.compile(r"[^A-Za-z0-9_.-]+")


@dataclass
class TrainingParameters:
    epochs: int = 100
    imgsz: int = 640
    batch: int = 8
    learning_rate: float = 0.01
    device: str = "auto"
    workers: int = 4
    seed: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TrainingPlan:
    store: DatasetStore
    base_model: str
    parameters: TrainingParameters
    run_id: str
    run_dir: Path
    dataset_info: YoloDatasetInfo
    dataset_metadata: DatasetMetadata
    result_json: Path
    command: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.store.dataset_id,
            "base_model": self.base_model,
            "parameters": self.parameters.to_dict(),
            "run_id": self.run_id,
            "run_dir": str(self.run_dir),
            "data_yaml": str(self.dataset_info.data_yaml),
            "class_names": self.dataset_info.class_names,
            "dataset_version": self.dataset_metadata.version,
            "dataset_revision": self.dataset_metadata.revision,
        }


def prepare_training(
    store: DatasetStore,
    base_model: str,
    training_root: Path | str,
    parameters: TrainingParameters,
    run_id: str | None = None,
) -> TrainingPlan:
    if not base_model.strip():
        raise ValueError("Valj en basmodell")
    dataset, metadata = store.load()
    if metadata.revision > 0:
        metadata = store.freeze_version()
        dataset, metadata = store.load()
    if not dataset.annotations:
        raise ValueError("Datasetet innehaller inga annotationer att trana pa")

    timestamp = datetime.now(timezone.utc)
    run_id = run_id or timestamp.strftime("run-%Y%m%d-%H%M%S-%f")
    run_id = _SAFE.sub("_", run_id)
    run_dir = Path(training_root) / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    dataset_info = prepare_yolo_dataset(store, run_dir / "dataset")
    result_json = run_dir / "result.json"

    command = [
        sys.executable,
        "-m",
        "xray_detector.training.train_entry",
        "--data",
        str(dataset_info.data_yaml),
        "--model",
        base_model,
        "--epochs",
        str(parameters.epochs),
        "--imgsz",
        str(parameters.imgsz),
        "--batch",
        str(parameters.batch),
        "--lr",
        str(parameters.learning_rate),
        "--device",
        parameters.device,
        "--workers",
        str(parameters.workers),
        "--seed",
        str(parameters.seed),
        "--project",
        str(run_dir),
        "--name",
        "train",
        "--result",
        str(result_json),
    ]
    plan = TrainingPlan(
        store=store,
        base_model=base_model,
        parameters=parameters,
        run_id=run_id,
        run_dir=run_dir,
        dataset_info=dataset_info,
        dataset_metadata=metadata,
        result_json=result_json,
        command=command,
    )
    atomic_write_json(run_dir / "plan.json", plan.to_dict())
    return plan


def finalize_training(plan: TrainingPlan, models_root: Path | str) -> tuple[ModelMetadata, Path]:
    metrics: dict[str, Any] = {}
    best_path: Path | None = None
    if plan.result_json.exists():
        data = read_json(plan.result_json)
        if data.get("error"):
            raise RuntimeError(f"Traningen misslyckades: {data['error']}")
        metrics = dict(data.get("metrics", {}))
        if data.get("best"):
            best_path = Path(str(data["best"]))
    if best_path is None or not best_path.exists():
        candidate = plan.run_dir / "train" / "weights" / "best.pt"
        if candidate.exists():
            best_path = candidate
    if best_path is None or not best_path.exists():
        raise FileNotFoundError("Traningen blev klar men inga modellvikter hittades")

    base_stem = _SAFE.sub("_", Path(plan.base_model).stem or "model")
    model_id = _SAFE.sub(
        "_",
        f"{base_stem}-{plan.store.dataset_id}-v{plan.dataset_metadata.version}-{plan.run_id}",
    )
    model_dir = Path(models_root) / model_id
    if model_dir.exists():
        raise FileExistsError(f"Modellkatalogen {model_dir} finns redan")
    model_dir.mkdir(parents=True)
    shutil.copy2(best_path, model_dir / "best.pt")

    metadata = ModelMetadata(
        model_id=model_id,
        base_model=plan.base_model,
        dataset_id=plan.store.dataset_id,
        dataset_version=plan.dataset_metadata.version,
        dataset_revision=plan.dataset_metadata.revision,
        created_at=utc_now_iso(),
        parameters=plan.parameters.to_dict(),
        metrics=metrics,
        class_names=plan.dataset_info.class_names,
    )
    write_model_metadata(metadata, model_dir / "metadata.json")
    return metadata, model_dir / "best.pt"
