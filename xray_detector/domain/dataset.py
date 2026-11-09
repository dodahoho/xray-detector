from dataclasses import dataclass

import numpy as np


@dataclass
class AnnotatedImage:
    frame: np.ndarray
    annotations: list[dict]
