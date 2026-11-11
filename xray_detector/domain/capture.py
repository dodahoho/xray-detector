from dataclasses import dataclass

import numpy as np

from xray_detector.domain.detection import Detection


@dataclass
class StreamFrame:
    source_id: str
    frame: np.ndarray
    detections: list[Detection]
    source_label: str
    sequence: int = 0
    fps: float | None = None


@dataclass(frozen=True)
class VideoMode:
    """En upplösning och ett pixelformat som en UVC-enhet erbjuder (TASK-39)."""

    width: int
    height: int
    fourcc: str = ""

    @property
    def label(self) -> str:
        return f"{self.width}x{self.height} {self.fourcc}".strip()
