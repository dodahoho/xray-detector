from abc import ABC, abstractmethod

import numpy as np

from xray_detector.domain.detection import Detection


class BaseDetector(ABC):
    def __init__(self, name: str, class_names: list[str]) -> None:
        self.name = name
        self.class_names = class_names

    @abstractmethod
    def detect(self, frame: np.ndarray) -> list[Detection]: ...
