from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pytest


@pytest.fixture
def frame() -> np.ndarray:
    image = np.zeros((120, 160, 3), dtype=np.uint8)
    image[:, :] = (10, 20, 30)
    return image
