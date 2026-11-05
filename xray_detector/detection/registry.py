from dataclasses import dataclass

from xray_detector.detection.base import BaseDetector


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
        from xray_detector.detection.yolo_detector import YoloDetector

        return YoloDetector(spec.weights, class_names, confidence_threshold)
    if spec.family == "rfdetr":
        from xray_detector.detection.rfdetr_detector import RfDetrDetector

        return RfDetrDetector(spec.weights, class_names, confidence_threshold)
    raise ValueError(f"Okänd modellfamilj: {spec.family}")


def spec_by_key(key: str) -> ModelSpec:
    for spec in MODEL_SPECS:
        if spec.key == key:
            return spec
    raise ValueError(f"Okänd modell: {key}")
