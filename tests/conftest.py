from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from xray_detector.dataset.pending import PendingCapture, create_pending_capture
from xray_detector.dataset.store import DatasetStore
from xray_detector.models import Detection
from xray_detector.util.paths import AppPaths


@pytest.fixture
def paths(tmp_path: Path) -> AppPaths:
    return AppPaths(tmp_path / "data").ensure()


@pytest.fixture
def store(paths: AppPaths) -> DatasetStore:
    store = DatasetStore(paths.datasets, "default")
    store.create(name="Test")
    return store


@pytest.fixture
def capture_factory(paths: AppPaths):
    def make_capture(index: int = 0) -> PendingCapture:
        frames = {
            "left": np.full((80, 100, 3), index, dtype=np.uint8),
            "right": np.full((80, 100, 3), index + 1, dtype=np.uint8),
        }
        detections = {
            "left": [Detection(10, 10, 40, 50, 0, "skruv", 0.9)],
            "right": [],
        }
        return create_pending_capture(
            paths.pending,
            frames,
            detections,
            group_id=f"group-{index:03d}",
        )

    return make_capture
