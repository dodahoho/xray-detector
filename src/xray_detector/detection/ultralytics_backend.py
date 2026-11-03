from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from xray_detector.detection.backend import DetectorBackend, DetectorError
from xray_detector.models import Detection

LOGGER = logging.getLogger(__name__)


def ultralytics_available() -> bool:
    try:
        import ultralytics  # noqa: F401
    except Exception:
        return False
    return True


class UltralyticsDetectorBackend(DetectorBackend):
    def __init__(
        self,
        model_path: str | Path,
        device: str = "auto",
        half: bool = True,
    ) -> None:
        self.model_path = str(model_path)
        self.requested_device = device
        self.half = half
        self.device = "cpu"
        self._model: Any = None
        self._names: dict[int, str] = {}

    def load(self) -> None:
        try:
            from ultralytics import YOLO
        except Exception as exc:  # pragma: no cover - beror pa installation
            raise DetectorError(
                "Ultralytics ar inte installerat. Kor: pip install -e \".[detection]\""
            ) from exc

        self.device = self._resolve_device(self.requested_device)
        try:
            self._model = YOLO(self.model_path)
            names = getattr(self._model, "names", {}) or {}
            self._names = {int(key): str(value) for key, value in names.items()}
            LOGGER.info("Modell %s laddad pa %s", self.model_path, self.device)
        except Exception as exc:
            raise DetectorError(f"Kunde inte ladda modellen {self.model_path}: {exc}") from exc

    @staticmethod
    def _resolve_device(requested: str) -> str:
        if requested and requested.lower() != "auto":
            return requested
        try:
            import torch

            if torch.cuda.is_available():
                return "0"
        except Exception:
            pass
        return "cpu"

    def detect(
        self,
        frame: np.ndarray,
        confidence: float,
        iou: float,
        class_filter: Sequence[int] | None = None,
    ) -> list[Detection]:
        if self._model is None:
            raise DetectorError("Modellen ar inte laddad")
        classes = list(class_filter) if class_filter else None
        try:
            results = self._model.predict(
                source=frame,
                conf=float(confidence),
                iou=float(iou),
                classes=classes,
                device=self.device,
                half=self.half and self.device != "cpu",
                verbose=False,
            )
        except Exception as exc:
            raise DetectorError(f"Detektion misslyckades: {exc}") from exc

        detections: list[Detection] = []
        for result in results:
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            for box in boxes:
                xyxy = box.xyxy[0].tolist()
                class_id = int(box.cls[0].item())
                score = float(box.conf[0].item())
                name = self._names.get(class_id, str(class_id))
                detections.append(
                    Detection(
                        x1=float(xyxy[0]),
                        y1=float(xyxy[1]),
                        x2=float(xyxy[2]),
                        y2=float(xyxy[3]),
                        class_id=class_id,
                        class_name=name,
                        confidence=score,
                    )
                )
        return detections

    @property
    def class_names(self) -> dict[int, str]:
        return dict(self._names)
