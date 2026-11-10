from abc import ABC, abstractmethod

import numpy as np

from xray_detector.domain.detection import Detection


class BaseDetector(ABC):
    def __init__(self, name: str, class_names: list[str]) -> None:
        self.name = name
        self.class_names = class_names
        self.confidence_threshold = 0.4

    def set_confidence_threshold(self, value: float) -> None:
        """Ändrar tröskeln utan att modellen laddas om (TASK-36)."""
        self.confidence_threshold = value

    @abstractmethod
    def detect(self, frame: np.ndarray) -> list[Detection]: ...
