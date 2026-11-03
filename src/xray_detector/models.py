from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Detection:
    """En detektion eller annotation i bildkoordinater (x1, y1, x2, y2)."""

    x1: float
    y1: float
    x2: float
    y2: float
    class_id: int
    class_name: str
    confidence: float = 1.0

    @property
    def xyxy(self) -> tuple[float, float, float, float]:
        return self.x1, self.y1, self.x2, self.y2

    def clamped(self, width: int, height: int) -> "Detection":
        x1 = min(max(self.x1, 0.0), float(width))
        y1 = min(max(self.y1, 0.0), float(height))
        x2 = min(max(self.x2, 0.0), float(width))
        y2 = min(max(self.y2, 0.0), float(height))
        if x2 < x1:
            x1, x2 = x2, x1
        if y2 < y1:
            y1, y2 = y2, y1
        return Detection(
            x1,
            y1,
            x2,
            y2,
            self.class_id,
            self.class_name,
            self.confidence,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "x1": self.x1,
            "y1": self.y1,
            "x2": self.x2,
            "y2": self.y2,
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Detection":
        return cls(
            x1=float(data["x1"]),
            y1=float(data["y1"]),
            x2=float(data["x2"]),
            y2=float(data["y2"]),
            class_id=int(data.get("class_id", 0)),
            class_name=str(data.get("class_name", "objekt")),
            confidence=float(data.get("confidence", 1.0)),
        )
