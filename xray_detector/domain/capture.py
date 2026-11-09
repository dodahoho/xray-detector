from dataclasses import dataclass

import numpy as np

from xray_detector.domain.detection import Detection


@dataclass
class StreamFrame:
    source_id: str
    frame: np.ndarray
    detections: list[Detection]
    source_label: str
