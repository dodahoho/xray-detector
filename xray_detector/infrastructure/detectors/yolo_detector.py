import numpy as np

from xray_detector.domain.detection import Detection
from xray_detector.infrastructure.detectors.base import BaseDetector


def resolve_device(requested: str) -> str:
    import torch

    if requested.startswith("cuda") and not torch.cuda.is_available():
        return "cpu"
    return requested


class YoloDetector(BaseDetector):
    def __init__(
        self,
        weights: str,
        class_names: list[str],
        confidence_threshold: float,
        device: str = "cuda",
    ) -> None:
        super().__init__(name=f"YOLO ({weights})", class_names=class_names)
        from ultralytics import YOLO

        from xray_detector.infrastructure.detectors.tuning import (
            configure_inference_threads,
        )

        configure_inference_threads()
        self.model = YOLO(weights)
        self.confidence_threshold = confidence_threshold
        self.device = resolve_device(device)

    @property
    def device_label(self) -> str:
        if self.device.startswith("cuda"):
            import torch

            try:
                name = torch.cuda.get_device_name(0)
            except Exception:
                name = "GPU"
            return f"CUDA ({name})"
        return "CPU (CUDA ej tillgänglig)"

    def detect(self, frame: np.ndarray) -> list[Detection]:
        result = self.model.predict(
            frame,
            conf=self.confidence_threshold,
            device=self.device,
            verbose=False,
        )[0]
        detections: list[Detection] = []
        names = result.names
        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            class_id = int(box.cls[0])
            detections.append(
                Detection(
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                    class_name=names.get(class_id, str(class_id))
                    if isinstance(names, dict)
                    else names[class_id],
                    confidence=float(box.conf[0]),
                )
            )
        return detections
