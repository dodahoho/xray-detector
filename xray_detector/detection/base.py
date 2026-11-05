from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass
class Detection:
    x1: float
    y1: float
    x2: float
    y2: float
    class_name: str
    confidence: float

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1


class BaseDetector(ABC):
    def __init__(self, name: str, class_names: list[str]) -> None:
        self.name = name
        self.class_names = class_names

    @abstractmethod
    def detect(self, frame: np.ndarray) -> list[Detection]: ...
