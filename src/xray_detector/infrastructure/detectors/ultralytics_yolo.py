"""Ultralytics YOLO detector adapter."""

from __future__ import annotations

import logging

import numpy as np

from xray_detector.config import DetectionSettings
from xray_detector.domain.detection import BBox, Detection, ModelMetadata
from xray_detector.infrastructure.detectors.base import Detector, DetectorUnavailable

logger = logging.getLogger(__name__)


class UltralyticsYoloDetector(Detector):
    family = "yolo"

    def __init__(self, metadata: ModelMetadata, settings: DetectionSettings) -> None:
        super().__init__(metadata)
        self.settings = settings
        self._model = None

    def load(self) -> None:
        try:
            from ultralytics import YOLO
        except Exception as exc:
            raise DetectorUnavailable(
                "Ultralytics is not installed. Install the ML extras with: uv sync --extra ml"
            ) from exc

        logger.info("Loading YOLO model %s from %s", self.metadata.name, self.metadata.path)
        try:
            self._model = YOLO(str(self.metadata.path))
        except Exception as exc:
            raise DetectorUnavailable(f"Could not load YOLO model: {exc}") from exc

        names = getattr(self._model, "names", None)
        if isinstance(names, dict):
            self.metadata.classes = {int(key): str(value) for key, value in names.items()}
        elif isinstance(names, list):
            self.metadata.classes = {index: str(value) for index, value in enumerate(names)}

    def predict(self, frame_bgr: np.ndarray) -> list[Detection]:
        if self._model is None:
            raise DetectorUnavailable("YOLO model is not loaded")
        # Ultralytics replaced the legacy `half` flag with `quantize` (16 = FP16, None = FP32).
        half = self.settings.half and not self.settings.device.lower().startswith("cpu")
        results = self._model.predict(
            source=frame_bgr,
            conf=self.settings.conf,
            iou=self.settings.iou,
            imgsz=self.settings.imgsz,
            device=self.settings.device,
            quantize=16 if half else None,
            verbose=False,
        )
        detections: list[Detection] = []
        if not results:
            return detections
        result = results[0]
        names = getattr(result, "names", None) or getattr(self._model, "names", {})
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            return detections
        for box in boxes:
            xyxy = box.xyxy[0].detach().cpu().numpy().tolist()
            score = float(box.conf[0].detach().cpu().numpy())
            class_id = int(box.cls[0].detach().cpu().numpy())
            if isinstance(names, dict):
                class_name = str(names.get(class_id, str(class_id)))
            else:
                class_name = str(class_id)
            detections.append(
                Detection(
                    bbox=BBox(*xyxy),
                    score=score,
                    class_id=class_id,
                    class_name=class_name,
                    source=self.metadata.id,
                )
            )
        return detections

    def close(self) -> None:
        self._model = None
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
