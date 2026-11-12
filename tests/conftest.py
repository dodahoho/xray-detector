"""Gemensamma fixtures: Qt-applikation, fake-detektor och syntetiska bilder."""

import gc

import cv2
import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from xray_detector.domain.config import AppConfig
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


@pytest.fixture(autouse=True)
def _collect_qt_objects():
    """River Qt-objekt mellan testerna i stället för inuti processEvents (TASK-34).

    Flera tester skapar MainWindow och DetectionView som aldrig stängs. Lämnas
    de till garbage collector kan de rivas inuti ett processEvents()-anrop i
    ett senare test, vilket kraschar med access violation. Genom att samla
    skräpet efter varje test rivs de på en säker punkt i stället.
    """
    yield
    gc.collect()


@pytest.fixture
def config(tmp_path) -> AppConfig:
    """AppConfig med dataset-, export- och loggkataloger under tmp_path."""
    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    return config


@pytest.fixture
def fake_detector():
    return FakeDetector()


def synthetic_frame(fill: int = 120, width: int = 64, height: int = 48) -> np.ndarray:
    """Grå BGR-bild utan kamera."""
    frame = np.full((height, width, 3), fill, dtype=np.uint8)
    return frame


@pytest.fixture
def video_file(tmp_path):
    """Tolv ramars videofil, så strömmar kan köras utan kamera."""
    path = tmp_path / "stream.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 60, (64, 48))
    assert writer.isOpened(), "mp4v-codec saknas i denna OpenCV-byggnad"
    for i in range(12):
        writer.write(synthetic_frame(fill=100 + i))
    writer.release()
    return path
