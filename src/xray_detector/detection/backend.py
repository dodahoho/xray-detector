from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

import numpy as np

from xray_detector.models import Detection


class DetectorError(RuntimeError):
    pass


class DetectorBackend(ABC):
    """Gemensamt granssnitt for detektionsmodeller."""

    @abstractmethod
    def load(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def detect(
        self,
        frame: np.ndarray,
        confidence: float,
        iou: float,
        class_filter: Sequence[int] | None = None,
    ) -> list[Detection]:
        raise NotImplementedError

    @property
    @abstractmethod
    def class_names(self) -> dict[int, str]:
        raise NotImplementedError
