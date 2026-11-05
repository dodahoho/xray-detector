"""Modellregistry – abstrakt bas + adaptrar för YOLO26 och RF-DETR.

Båda modellerna drivs via Ultralytics' YOLO-klass (ultralytics stödjer både
YOLO och RF-DETR-vikter med samma API).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
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


def resolve_device(device: int | str) -> int | str:
    """Returnera en enhet som Ultralytics kan använda.

    Faller tillbaka på ``"cpu"`` när CUDA inte är tillgängligt eller när ett
    ogiltigt GPU-index angetts. Config använder ``-1`` för CPU.
    """
    if isinstance(device, str):
        value = device.strip().lower()
        if value in ("", "cpu"):
            return "cpu"
        value = value.removeprefix("cuda:")
        try:
            device = int(value)
        except ValueError:
            logger.warning("Okänt device '{}' – använder CPU", device)
            return "cpu"

    if device < 0:
        return "cpu"

    try:
        import torch
    except Exception as e:  # noqa: BLE001
        logger.warning("PyTorch kunde inte importeras ({}) – använder CPU", e)
        return "cpu"

    if not torch.cuda.is_available():
        return "cpu"

    count = torch.cuda.device_count()
    if device >= count:
        logger.warning(
            "GPU-index {} finns inte ({} GPU:er) – använder GPU 0",
            device, count,
        )
        return 0
    return device


class BaseModel(ABC):
    """Abstrakt detektionsmodell."""

    def __init__(self, path: str | Path, device: int | str = 0, quantize: str = "fp16"):
        self.path = str(path)
        self.device = device
        self.quantize = quantize
        self._model = None
        self._classes: list[str] = []
        self._runtime_device: int | str | None = None

    def _effective_device(self) -> int | str:
        """Faktisk enhet – faller tillbaka på CPU om CUDA saknas."""
        if self._runtime_device is None:
            self._runtime_device = resolve_device(self.device)
            if self._runtime_device == "cpu" and self.device not in ("cpu", -1):
                logger.warning(
                    "Ingen CUDA-enhet tillgänglig – {} körs på CPU",
                    Path(self.path).name,
                )
        return self._runtime_device

    def _effective_quantize(self) -> str:
        """Precision som skickas till Ultralytics.

        Endast ``fp16``/``fp32`` är relevanta för inferens. På CPU tvingas
        FP32 eftersom FP16 inte stöds där.
        """
        if self._effective_device() == "cpu":
            return "fp32"
        value = str(self.quantize).strip().lower()
        return "fp16" if value in ("fp16", "16", "half", "true") else "fp32"

    @abstractmethod
    def _load(self) -> None:
        """Ladda modellen."""

    def load(self) -> None:
        if self._model is None:
            logger.info("Laddar modell {} (device={}, quantize={})",
                        self.path, self._effective_device(),
                        self._effective_quantize())
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
            self._model.predict(
                dummy,
                device=self._effective_device(),
                quantize=self._effective_quantize(),
                verbose=False,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("Värmup misslyckades: {}", e)

    def predict(self, frame: np.ndarray, conf: float = 0.4, iou: float = 0.5) -> list[Detection]:
        if self._model is None:
            self.load()
        results = self._model.predict(
            frame,
            device=self._effective_device(),
            quantize=self._effective_quantize(),
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


def create_model(path: str | Path, device: int | str = 0, quantize: str = "fp16") -> BaseModel:
    """Fabrik: skapar en modell från en .pt-fil."""
    return UltralyticsModel(path, device=device, quantize=quantize)
