"""Roboflow RF-DETR detector adapter."""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from xray_detector.config import DetectionSettings
from xray_detector.domain.detection import BBox, Detection, ModelMetadata
from xray_detector.infrastructure.detectors.base import Detector, DetectorUnavailable

logger = logging.getLogger(__name__)


class RfDetrDetector(Detector):
    family = "rfdetr"

    def __init__(self, metadata: ModelMetadata, settings: DetectionSettings) -> None:
        super().__init__(metadata)
        self.settings = settings
        self._model = None

    def _model_class(self):
        try:
            import rfdetr
        except Exception as exc:
            raise DetectorUnavailable(
                "RF-DETR is not installed. Install the ML extras with: uv sync --extra ml"
            ) from exc

        hint = (
            f"{self.metadata.id} {self.metadata.path} "
            f"{self.metadata.manifest.get('base_model', '')} "
            f"{self.metadata.manifest.get('base_model_path', '')}"
        ).lower()
        if "large" in hint and hasattr(rfdetr, "RFDETRLarge"):
            return rfdetr.RFDETRLarge
        if hasattr(rfdetr, "RFDETRBase"):
            return rfdetr.RFDETRBase
        raise DetectorUnavailable("Installed rfdetr package has no RFDETRBase/RFDETRLarge class")

    def load(self) -> None:
        model_class = self._model_class()
        path = Path(str(self.metadata.path))
        logger.info("Loading RF-DETR model %s (%s)", self.metadata.name, path)
        try:
            if path.exists() and hasattr(model_class, "from_checkpoint"):
                self._model = model_class.from_checkpoint(str(path))
            else:
                kwargs = {}
                if path.exists():
                    kwargs["pretrain_weights"] = str(path)
                try:
                    self._model = model_class(**kwargs)
                except TypeError:
                    self._model = model_class()
        except Exception as exc:
            raise DetectorUnavailable(f"Could not load RF-DETR model: {exc}") from exc

        names = getattr(self._model, "class_names", None)
        if names is None:
            names = getattr(self._model, "classes", None)
        if isinstance(names, dict):
            self.metadata.classes = {int(key): str(value) for key, value in names.items()}
        elif isinstance(names, (list, tuple)):
            self.metadata.classes = {index: str(value) for index, value in enumerate(names)}

    def predict(self, frame_bgr: np.ndarray) -> list[Detection]:
        if self._model is None:
            raise DetectorUnavailable("RF-DETR model is not loaded")
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        try:
            from PIL import Image

            image = Image.fromarray(rgb)
        except Exception:
            image = rgb

        try:
            result = self._model.predict(image, threshold=self.settings.conf)
        except TypeError:
            result = self._model.predict(image)

        detections: list[Detection] = []
        xyxy = getattr(result, "xyxy", None)
        if xyxy is None:
            return detections
        confidence = getattr(result, "confidence", None)
        class_ids = getattr(result, "class_id", None)
        class_names = getattr(result, "class_name", None)
        data = getattr(result, "data", None)

        for index, coords in enumerate(xyxy):
            score = float(confidence[index]) if confidence is not None else 1.0
            if score < self.settings.conf:
                continue
            class_id = int(class_ids[index]) if class_ids is not None else 0
            class_name = None
            if class_names is not None:
                class_name = str(class_names[index])
            elif isinstance(data, dict) and "class_name" in data:
                class_name = str(data["class_name"][index])
            if not class_name:
                class_name = self.metadata.classes.get(class_id, str(class_id))
            detections.append(
                Detection(
                    bbox=BBox(
                        float(coords[0]), float(coords[1]), float(coords[2]), float(coords[3])
                    ),
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
