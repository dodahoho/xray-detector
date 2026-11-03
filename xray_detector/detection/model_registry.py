"""Modellregistry – abstrakt bas + adaptrar för YOLO26 och RF-DETR.

Båda modellerna drivs via Ultralytics' YOLO-klass (ultralytics stödjer både
YOLO och RF-DETR-vikter med samma API).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from loguru import logger


@dataclass
class Detection:
    """En detekterad objekt."""
    x1: float
    y1: float
    x2: float
    y2: float
    conf: float
    class_id: int
    class_name: str

    def to_dict(self) -> dict:
        return {
            "x1": self.x1, "y1": self.y1, "x2": self.x2, "y2": self.y2,
            "conf": self.conf, "class_id": self.class_id,
            "class_name": self.class_name,
        }


class BaseModel(ABC):
    """Abstrakt detektionsmodell."""

    def __init__(self, path: str | Path, device: int = 0, half: bool = True):
        self.path = str(path)
        self.device = device
        self.half = half
        self._model = None
        self._classes: list[str] = []

    @abstractmethod
    def _load(self) -> None:
        """Ladda modellen."""

    def load(self) -> None:
        if self._model is None:
            logger.info("Laddar modell {} (device={}, half={})",
                        self.path, self.device, self.half)
            self._load()

    @property
    def classes(self) -> list[str]:
        return list(self._classes)

    @abstractmethod
    def predict(self, frame: np.ndarray, conf: float = 0.4, iou: float = 0.5) -> list[Detection]:
        """Kör inferens på ett frame (BGR). Returnerar list av Detection."""

    def close(self) -> None:
        self._model = None


class UltralyticsModel(BaseModel):
    """Generisk adapter för Ultralytics-baserade modeller (YOLO26, RF-DETR)."""

    def _load(self) -> None:
        from ultralytics import YOLO
        self._model = YOLO(self.path)
        # Hämta klassnamn
        try:
            self._classes = list(self._model.names.values())
        except Exception:  # noqa: BLE001
            self._classes = []
        # Värm upp (kompilerar CUDA-kärnor)
        try:
            dummy = np.zeros((640, 640, 3), dtype=np.uint8)
            self._model.predict(dummy, device=self.device, half=self.half, verbose=False)
        except Exception as e:  # noqa: BLE001
            logger.warning("Värmup misslyckades: {}", e)

    def predict(self, frame: np.ndarray, conf: float = 0.4, iou: float = 0.5) -> list[Detection]:
        if self._model is None:
            self.load()
        results = self._model.predict(
            frame,
            device=self.device,
            half=self.half,
            conf=conf,
            iou=iou,
            verbose=False,
        )
        dets: list[Detection] = []
        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                x1, y1, x2, y2 = (float(v) for v in box.xyxy[0].tolist())
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                cls_name = self._classes[cls_id] if cls_id < len(self._classes) else str(cls_id)
                dets.append(Detection(x1, y1, x2, y2, conf, cls_id, cls_name))
        return dets


def create_model(path: str | Path, device: int = 0, half: bool = True) -> BaseModel:
    """Fabrik: skapar en modell från en .pt-fil."""
    return UltralyticsModel(path, device=device, half=half)
