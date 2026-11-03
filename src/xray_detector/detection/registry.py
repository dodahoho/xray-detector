from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from xray_detector.training.manifest import read_model_metadata

BUILTIN_MODELS = [
    "yolo11n.pt",
    "yolo11s.pt",
    "yolo11m.pt",
    "yolo11l.pt",
    "yolo11x.pt",
    "yolov8n.pt",
    "yolov8s.pt",
]


@dataclass(frozen=True)
class ModelInfo:
    model_id: str
    path: Path
    backend: str = "ultralytics"
    description: str = ""


def available_models(models_root: Path | str) -> list[ModelInfo]:
    root = Path(models_root)
    models = [ModelInfo(model_id=name, path=Path(name), description="Forinstalld YOLO-modell") for name in BUILTIN_MODELS]
    if not root.exists():
        return models
    for directory in sorted(root.iterdir()):
        weights = directory / "best.pt"
        if not directory.is_dir() or not weights.exists():
            continue
        description = ""
        metadata_path = directory / "metadata.json"
        if metadata_path.exists():
            try:
                metadata = read_model_metadata(metadata_path)
                description = f"Dataset v{metadata.dataset_version} ({metadata.dataset_id})"
            except (OSError, KeyError, ValueError):
                description = "Tranad modell"
        models.append(
            ModelInfo(
                model_id=directory.name,
                path=weights,
                backend="ultralytics",
                description=description,
            )
        )
    return models
