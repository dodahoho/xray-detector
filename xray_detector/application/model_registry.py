from dataclasses import dataclass
from json import load as json_load
from pathlib import Path

from xray_detector.infrastructure.detectors.base import BaseDetector


@dataclass(frozen=True)
class ModelSpec:
    key: str
    label: str
    family: str
    weights: str


MODEL_SPECS: list[ModelSpec] = [
    ModelSpec("yolo26n", "YOLO26 nano", "yolo", "yolo26n.pt"),
    ModelSpec("yolo26s", "YOLO26 small", "yolo", "yolo26s.pt"),
    ModelSpec("yolo26m", "YOLO26 medium", "yolo", "yolo26m.pt"),
    ModelSpec("rfdetr-base", "RF-DETR base", "rfdetr", "rfdetr-base"),
]


def create_detector(
    spec: ModelSpec,
    class_names: list[str],
    confidence_threshold: float,
) -> BaseDetector:
    if spec.family == "yolo":
        from xray_detector.infrastructure.detectors.yolo_detector import YoloDetector

        return YoloDetector(spec.weights, class_names, confidence_threshold)
    if spec.family == "rfdetr":
        from xray_detector.infrastructure.detectors.rfdetr_detector import RfDetrDetector

        return RfDetrDetector(spec.weights, class_names, confidence_threshold)
    raise ValueError(f"Okänd modellfamilj: {spec.family}")


def spec_by_key(key: str) -> ModelSpec:
    for spec in MODEL_SPECS:
        if spec.key == key:
            return spec
    raise ValueError(f"Okänd modell: {key}")


def trained_models(models_dir: Path) -> list[ModelSpec]:
    """Listar nytränade modeller utifrån training_manifest.json i models/v*/."""
    specs: list[ModelSpec] = []
    for manifest_path in sorted(models_dir.glob("v*/training_manifest.json")):
        try:
            with open(manifest_path, encoding="utf-8") as file:
                manifest = json_load(file)
            weights = manifest_path.parent / manifest.get("weights_relative", "")
            if not weights.exists():
                continue
        except (OSError, ValueError):
            continue
        version_dir = manifest_path.parent.name
        base = Path(manifest.get("base_weights", "modell")).stem
        classes = ", ".join(manifest.get("classes", []))
        label = f"Tränad {version_dir} ({base})" + (f" [{classes}]" if classes else "")
        specs.append(
            ModelSpec(key=f"trained-{version_dir}", label=label,
                      family="yolo", weights=str(weights))
        )
    return specs


def device_status() -> tuple[str, str]:
    """Returnerar (statusText, CSS-färg) för enhetsindikatorn i GUI:t."""
    try:
        import torch

        if torch.cuda.is_available():
            return f"Enhet: CUDA ({torch.cuda.get_device_name(0)})", "#2a8"
        return "Enhet: CPU (CUDA ej tillgänglig)", "#c33"
    except ImportError:
        return "Enhet: PyTorch saknas", "#c33"
