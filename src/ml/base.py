from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional
import cv2
import numpy as np

from src.core.models_schema import BoundingBox, TrainingConfig, TrainedModelInfo


class BaseDetector(ABC):
    """Gemensamt gränssnitt för alla detektionsmodeller (YOLO26, RF-DETR, etc.)."""

    def __init__(
        self,
        model_family: str,
        weights_path: str = "",
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.45,
    ) -> None:
        self.model_family = model_family
        self.weights_path = weights_path
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.is_loaded = False

    @abstractmethod
    def load(self) -> None:
        """Laddar modellvikter till GPU/CPU."""

    @abstractmethod
    def unload(self) -> None:
        """Frigör modell och GPU-minne (t.ex. under träning)."""

    @abstractmethod
    def predict(self, frame_bgr: np.ndarray) -> List[BoundingBox]:
        """Kör detektion på en bildruta (BGR) och returnerar en lista av BoundingBox."""


class BaseTrainer(ABC):
    """Gemensamt gränssnitt för modellträning."""

    @abstractmethod
    def train(
        self,
        config: TrainingConfig,
        output_dir: str,
        progress_callback: Callable[[int, int, Dict[str, float], str], None],
        stop_requested: Callable[[], bool],
    ) -> TrainedModelInfo:
        """Utför träning och sparar modellvikter med samma versionssiffra som datasetet."""


class SimulatedXrayDetector(BaseDetector):
    """Snabb röntgendetektor (densitets-/konturbaserad) som fungerar direkt utan externa nedladdningar.

    Används både som inbyggd referensdetektor och som sömlös reserv om en extern viktfil saknas offline.
    """

    def load(self) -> None:
        self.is_loaded = True

    def unload(self) -> None:
        self.is_loaded = False

    def predict(self, frame_bgr: np.ndarray) -> List[BoundingBox]:
        if not self.is_loaded or frame_bgr is None or frame_bgr.size == 0:
            return []

        h, w = frame_bgr.shape[:2]
        boxes: List[BoundingBox] = []

        # Ignorera rullbandets över- och underkant (48 px)
        roi_y1, roi_y2 = min(50, h // 6), max(h - 50, h - h // 6)
        roi = frame_bgr[roi_y1:roi_y2, :]
        if roi.size == 0:
            return []

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        # 1. Hög-densitet metallföremål (mörkblå/mörk i röntgenbild)
        mask_metal = cv2.inRange(roi, (10, 10, 5), (110, 65, 50))
        boxes.extend(
            self._extract_boxes(
                mask_metal,
                offset_y=roi_y1,
                class_name="Metallföremål",
                base_conf=0.92,
            )
        )

        # 2. Batteri / Elektronik (grön signatur i dual-energy X-ray)
        mask_battery = cv2.inRange(hsv, (35, 45, 35), (85, 255, 160))
        boxes.extend(
            self._extract_boxes(
                mask_battery,
                offset_y=roi_y1,
                class_name="Batteri",
                base_conf=0.88,
            )
        )

        return [b for b in boxes if b.confidence >= self.confidence_threshold]

    @staticmethod
    def _extract_boxes(
        mask: np.ndarray,
        offset_y: int,
        class_name: str,
        base_conf: float,
    ) -> List[BoundingBox]:
        kernel = np.ones((7, 7), np.uint8)
        closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        found: List[BoundingBox] = []
        for cnt in contours:
            x, y, bw, bh = cv2.boundingRect(cnt)
            if bw >= 35 and bh >= 35 and (bw * bh) >= 1800:
                found.append(
                    BoundingBox(
                        x1=float(x),
                        y1=float(y + offset_y),
                        x2=float(x + bw),
                        y2=float(y + offset_y + bh),
                        class_name=class_name,
                        confidence=round(base_conf, 2),
                        is_manual=False,
                    )
                )
        return found
