from dataclasses import dataclass
from typing import Any


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

    def to_dict(self) -> dict[str, Any]:
        """Detektionen som JSON-vänliga värden (TASK-146)."""
        return {
            "x1": self.x1,
            "y1": self.y1,
            "x2": self.x2,
            "y2": self.y2,
            "class_name": self.class_name,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Detection":
        """Läser en detektion ur JSON; confidence saknas i äldre pending-filer."""
        return cls(
            x1=float(data["x1"]),
            y1=float(data["y1"]),
            x2=float(data["x2"]),
            y2=float(data["y2"]),
            class_name=str(data["class_name"]),
            confidence=float(data.get("confidence", 1.0)),
        )
