"""Gemensamma fixtures: Qt-applikation, fake-detektor och syntetiska bilder."""

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from xray_detector.domain.detection import Detection
from xray_detector.infrastructure.detectors.base import BaseDetector


class FakeDetector(BaseDetector):
    """Detektor utan modell eller GPU: räknar alltid ut en fast rektangel."""

    def __init__(self, class_name: str = "kniv") -> None:
        super().__init__(name="fake", class_names=[class_name])
        self.class_name = class_name

    def detect(self, frame: np.ndarray) -> list[Detection]:
        height, width = frame.shape[:2]
        w = max(4, width // 4)
        h = max(4, height // 4)
        return [Detection(2, 2, 2 + w, 2 + h, self.class_name, 0.9)]


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def fake_detector():
    return FakeDetector()


def synthetic_frame(fill: int = 120, width: int = 64, height: int = 48) -> np.ndarray:
    """Grå BGR-bild utan kamera."""
    frame = np.full((height, width, 3), fill, dtype=np.uint8)
    return frame
