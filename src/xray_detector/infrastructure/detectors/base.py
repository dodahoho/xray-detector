"""Common detector interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np

from xray_detector.domain.detection import BBox, Detection, ModelMetadata


class DetectorError(RuntimeError):
    """Raised when a detector cannot be loaded or used."""


class DetectorUnavailable(DetectorError):
    """Raised when optional ML dependencies are not installed."""


class Detector(ABC):
    family: str = "unknown"

    def __init__(self, metadata: ModelMetadata) -> None:
        self.metadata = metadata

    @abstractmethod
    def load(self) -> None: ...

    @abstractmethod
    def predict(self, frame_bgr: np.ndarray) -> list[Detection]: ...

    def close(self) -> None:
        return None

    @property
    def classes(self) -> dict[int, str]:
        return dict(self.metadata.classes)


class FakeDetector(Detector):
    """Deterministic detector used by tests and UI smoke tests."""

    family = "fake"

    def __init__(
        self,
        metadata: ModelMetadata | None = None,
        boxes: list[tuple[float, float, float, float]] | None = None,
        class_name: str = "object",
        score: float = 0.9,
    ) -> None:
        if metadata is None:
            metadata = ModelMetadata(
                id="fake",
                name="Fake detector",
                family="fake",
                path=Path("fake"),
                classes={0: class_name},
            )
        super().__init__(metadata)
        self._boxes = boxes
        self._class_name = class_name
        self._score = score
        self._loaded = False

    def load(self) -> None:
        self._loaded = True

    def predict(self, frame_bgr: np.ndarray) -> list[Detection]:
        if not self._loaded:
            self.load()
        height, width = frame_bgr.shape[:2]
        boxes = self._boxes or [
            (width * 0.2, height * 0.2, width * 0.6, height * 0.7),
        ]
        return [
            Detection(
                bbox=BBox(*box),
                score=self._score,
                class_id=0,
                class_name=self._class_name,
                source="fake",
            )
            for box in boxes
        ]
