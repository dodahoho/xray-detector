from dataclasses import dataclass, replace
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
    ModelSpec("rfdetr-nano", "RF-DETR nano", "rfdetr", "rfdetr-nano"),
    ModelSpec("rfdetr-small", "RF-DETR small", "rfdetr", "rfdetr-small"),
    ModelSpec("rfdetr-medium", "RF-DETR medium", "rfdetr", "rfdetr-medium"),
    ModelSpec("rfdetr-large", "RF-DETR large", "rfdetr", "rfdetr-large"),
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


def base_models(models_dir: Path) -> list[ModelSpec]:
    """Basmodellerna med YOLO-vikterna under models_dir (TASK-50).

    Ultralytics laddar ner en saknad vikt till den sökväg den får, så
    basvikterna hamnar i models/ i stället för i arbetskatalogen. RF-DETR
    bygger modellen ur paketet och behåller därför sitt storleksnamn.
    """
    return [
        replace(spec, weights=str(Path(models_dir) / spec.weights))
        if spec.family == "yolo"
        else spec
        for spec in MODEL_SPECS
    ]


def trained_models(trained_dir: Path) -> list[ModelSpec]:
    """Listar egentränade modeller utifrån training_manifest.json under models/trained/.

    Sökningen är rekursiv så att varje träningskörnings egen katalog
    (v<version> eller en framtida snapshotkatalog) hittas var för sig.
    """
    trained_dir = Path(trained_dir)
    specs: list[ModelSpec] = []
    for manifest_path in sorted(trained_dir.rglob("training_manifest.json")):
        try:
            with open(manifest_path, encoding="utf-8") as file:
                manifest = json_load(file)
            weights = manifest_path.parent / manifest.get("weights_relative", "")
            if not weights.exists():
                continue
            run_dir = manifest_path.parent.relative_to(trained_dir).as_posix()
        except (OSError, ValueError):
            continue
        base = Path(manifest.get("base_weights", "modell")).stem
        classes = ", ".join(manifest.get("classes", []))
        label = f"Tränad {run_dir} ({base})" + (f" [{classes}]" if classes else "")
        specs.append(
            ModelSpec(key=f"trained-{run_dir}", label=label,
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
