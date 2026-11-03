"""Detection and bounding-box primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class BBox:
    """Axis-aligned bounding box in absolute pixel coordinates (xyxy)."""

    x1: float
    y1: float
    x2: float
    y2: float

    def __post_init__(self) -> None:
        x1, x2 = sorted((float(self.x1), float(self.x2)))
        y1, y2 = sorted((float(self.y1), float(self.y2)))
        object.__setattr__(self, "x1", x1)
        object.__setattr__(self, "y1", y1)
        object.__setattr__(self, "x2", x2)
        object.__setattr__(self, "y2", y2)

    @property
    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)

    @property
    def area(self) -> float:
        return self.width * self.height

    def is_valid(self, min_size: float = 1.0) -> bool:
        return self.width >= min_size and self.height >= min_size

    def clip(self, width: int, height: int) -> BBox:
        return BBox(
            min(max(self.x1, 0.0), float(width)),
            min(max(self.y1, 0.0), float(height)),
            min(max(self.x2, 0.0), float(width)),
            min(max(self.y2, 0.0), float(height)),
        )

    def to_xywh(self) -> tuple[float, float, float, float]:
        return self.x1, self.y1, self.width, self.height

    def to_normalized(self, width: int, height: int) -> tuple[float, float, float, float]:
        if width <= 0 or height <= 0:
            return 0.0, 0.0, 0.0, 0.0
        return (
            self.x1 / width,
            self.y1 / height,
            self.width / width,
            self.height / height,
        )

    @classmethod
    def from_xywh(cls, x: float, y: float, w: float, h: float) -> BBox:
        return cls(x, y, x + w, y + h)

    @classmethod
    def from_normalized(
        cls, x: float, y: float, w: float, h: float, width: int, height: int
    ) -> BBox:
        return cls(x * width, y * height, (x + w) * width, (y + h) * height)


@dataclass(frozen=True)
class Detection:
    """A single detector output for one frame."""

    bbox: BBox
    score: float
    class_id: int
    class_name: str
    source: str | None = None


@dataclass
class ModelMetadata:
    """Metadata describing a detector/model artifact."""

    id: str
    name: str
    family: str
    path: Path
    classes: dict[int, str] = field(default_factory=dict)
    trained: bool = False
    manifest: dict = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        if self.trained:
            version = self.manifest.get("dataset_version", "")
            return f"{self.name} ({version})" if version else self.name
        return self.name


@dataclass(frozen=True)
class FramePacket:
    """A video frame with a monotonically increasing sequence number."""

    role: str
    sequence: int
    frame: np.ndarray
    timestamp: float

    @property
    def shape(self) -> tuple[int, int]:
        height, width = self.frame.shape[:2]
        return width, height


@dataclass
class CaptureSnapshot:
    """Frozen frames and detections captured from both streams."""

    frames: dict[str, np.ndarray]
    detections: dict[str, list[Detection]]
    sequences: dict[str, int]
    captured_at: str
    pair_id: str
