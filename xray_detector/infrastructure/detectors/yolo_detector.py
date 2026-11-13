import numpy as np

from xray_detector.domain.detection import Detection
from xray_detector.domain.model_input import round_size
from xray_detector.infrastructure.detectors.base import BaseDetector, class_names_from


def input_size_for(frame: np.ndarray) -> tuple[int, int]:
    """Inferensens bildstorlek följer källans upplösning (TASK-79).

    Ultralytics letterboxar annars varje ram till modellens standardstorlek
    (640), så en 1080p-ström tappade detaljer innan modellen såg dem. Mätt på
    RTX 5080 kostar 1088x1920 samma tid som 640 för yolo26n, eftersom
    förbehandlingen på CPU är den dyra delen.
    """
    height, width = frame.shape[:2]
    return round_size(height), round_size(width)


def resolve_device(requested: str) -> str:
    import torch

    if requested.startswith("cuda") and not torch.cuda.is_available():
        return "cpu"
    return requested


class YoloDetector(BaseDetector):
    def __init__(
        self,
        weights: str,
        confidence_threshold: float,
        device: str = "cuda",
    ) -> None:
        from ultralytics import YOLO

        from xray_detector.infrastructure.detectors.tuning import (
            configure_inference_threads,
        )

        configure_inference_threads()
        model = YOLO(weights)
        super().__init__(
            name=f"YOLO ({weights})",
            class_names=class_names_from(getattr(model, "names", None), weights),
        )
        self.model = model
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
            imgsz=input_size_for(frame),
            verbose=False,
        )[0]
        detections: list[Detection] = []
        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            detections.append(
                Detection(
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                    class_name=self._class_name(int(box.cls[0])),
                    confidence=float(box.conf[0]),
                )
            )
        return self.filter_detections(detections)

    def _class_name(self, class_id: int) -> str:
        """Modellens klassnamn för id:t; id:t självt om listan är kortare."""
        if 0 <= class_id < len(self.class_names):
            return self.class_names[class_id]
        return str(class_id)
