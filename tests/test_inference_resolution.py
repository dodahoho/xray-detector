"""Inferensen använder källans upplösning i stället för ultralytics 640 (TASK-79)."""

import sys
import types

import numpy as np

from xray_detector.domain.model_input import MAX_SIZE, MIN_SIZE, round_size


def _frame(width: int, height: int) -> np.ndarray:
    return np.zeros((height, width, 3), dtype=np.uint8)


class _FakeResult:
    def __init__(self) -> None:
        self.boxes: list = []


class _FakeYoloModel:
    """Minsta ultralytics-modell: klassnamn och inspelade predict-anrop."""

    def __init__(self) -> None:
        self.names = {0: "kniv"}
        self.calls: list[dict] = []

    def predict(self, frame, **kwargs):
        self.calls.append(kwargs)
        return [_FakeResult()]


def _fake_ultralytics(monkeypatch, model) -> None:
    fake = types.ModuleType("ultralytics")
    fake.YOLO = lambda weights: model
    monkeypatch.setitem(sys.modules, "ultralytics", fake)


def test_round_size_rounds_up_to_the_stride():
    assert round_size(1080) == 1088
    assert round_size(1920) == 1920
    assert round_size(640) == 640


def test_round_size_stays_within_the_limits():
    assert round_size(100) == MIN_SIZE
    assert round_size(4000) == MAX_SIZE


def test_input_size_follows_the_frame():
    from xray_detector.infrastructure.detectors.yolo_detector import input_size_for

    assert input_size_for(_frame(1920, 1080)) == (1088, 1920)
    assert input_size_for(_frame(640, 480)) == (480, 640)


def test_yolo_detects_at_the_source_resolution(monkeypatch):
    """En 1080p-ram skickas som 1088x1920 i stället för modellens 640."""
    model = _FakeYoloModel()
    _fake_ultralytics(monkeypatch, model)

    from xray_detector.infrastructure.detectors.yolo_detector import YoloDetector

    detector = YoloDetector("models/yolo26n.pt", 0.4)
    detector.detect(_frame(1920, 1080))
    detector.detect(_frame(640, 480))

    assert [call["imgsz"] for call in model.calls] == [(1088, 1920), (480, 640)]


def test_yolo_keeps_the_threshold_and_device(monkeypatch):
    """Upplösningen ändrar inte de andra argumenten till predict."""
    model = _FakeYoloModel()
    _fake_ultralytics(monkeypatch, model)

    from xray_detector.infrastructure.detectors.yolo_detector import YoloDetector

    detector = YoloDetector("models/yolo26n.pt", 0.55)
    detector.detect(_frame(800, 600))

    assert model.calls[-1]["conf"] == 0.55
    assert model.calls[-1]["device"] == detector.device
