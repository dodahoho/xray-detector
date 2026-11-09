from dataclasses import dataclass


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
