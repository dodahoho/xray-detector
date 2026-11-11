"""Klassnamnen kommer från modellen, inte från AppConfig.classes (TASK-52)."""

import inspect
import sys
import types

import numpy as np
import pytest
from PySide6.QtCore import QSettings

from tests.conftest import FakeDetector
from xray_detector.application import model_registry
from xray_detector.domain.config import AppConfig


class _FakeBox:
    def __init__(self, xyxy, class_id, confidence):
        self.xyxy = np.array([xyxy], dtype=float)
        self.cls = np.array([class_id])
        self.conf = np.array([confidence])


class _FakeResult:
    def __init__(self, boxes):
        self.boxes = boxes


class _FakeYoloModel:
    """Minsta ultralytics-modell: klassnamnen på modellen och fasta rutor."""

    def __init__(self, names, boxes=()):
        self.names = names
        self.boxes = list(boxes)
        self.calls = []

    def predict(self, frame, **kwargs):
        self.calls.append(kwargs)
        return [_FakeResult(self.boxes)]


def _fake_ultralytics(monkeypatch, model):
    fake = types.ModuleType("ultralytics")
    fake.YOLO = lambda weights: model
    monkeypatch.setitem(sys.modules, "ultralytics", fake)
    return model


class _FakeRfDetrModel:
    def __init__(self, class_names):
        self.class_names = class_names

    def inference(self, **kwargs):
        pass


def _fake_rfdetr(monkeypatch, model):
    fake = types.ModuleType("rfdetr")
    fake.RFDETRSmall = lambda: model
    monkeypatch.setitem(sys.modules, "rfdetr", fake)
    return model


# --- YOLO (AC 1, 2, 4) ---


def test_yolo_reads_class_names_from_the_weights(monkeypatch):
    _fake_ultralytics(monkeypatch, _FakeYoloModel({0: "kniv", 1: "pistol"}))

    from xray_detector.infrastructure.detectors.yolo_detector import YoloDetector

    detector = YoloDetector("models/yolo26n.pt", 0.4)

    assert detector.class_names == ["kniv", "pistol"]


def test_yolo_names_detections_from_the_model(monkeypatch):
    _fake_ultralytics(
        monkeypatch,
        _FakeYoloModel({0: "kniv", 1: "pistol"}, [_FakeBox([1, 2, 11, 22], 1, 0.8)]),
    )

    from xray_detector.infrastructure.detectors.yolo_detector import YoloDetector

    detector = YoloDetector("vikter.pt", 0.4)
    detections = detector.detect(np.zeros((10, 10, 3), np.uint8))

    assert [(d.class_name, round(d.confidence, 2)) for d in detections] == [
        ("pistol", 0.8)
    ]


def test_yolo_without_class_names_gives_a_clear_error(monkeypatch):
    _fake_ultralytics(monkeypatch, _FakeYoloModel(None))

    from xray_detector.infrastructure.detectors.yolo_detector import YoloDetector

    with pytest.raises(ValueError, match="Kunde inte läsa klassnamnen ur vikter.pt"):
        YoloDetector("vikter.pt", 0.4)


# --- RF-DETR (AC 1, 2, 4) ---


def test_rfdetr_reads_class_names_from_the_model(monkeypatch):
    _fake_rfdetr(monkeypatch, _FakeRfDetrModel(["kniv", "pistol"]))

    from xray_detector.infrastructure.detectors.rfdetr_detector import RfDetrDetector

    detector = RfDetrDetector("rfdetr-small", 0.4)

    assert detector.class_names == ["kniv", "pistol"]


def test_rfdetr_without_class_names_gives_a_clear_error(monkeypatch):
    _fake_rfdetr(monkeypatch, _FakeRfDetrModel(None))

    from xray_detector.infrastructure.detectors.rfdetr_detector import RfDetrDetector

    with pytest.raises(ValueError, match="Kunde inte läsa klassnamnen ur rfdetr-small"):
        RfDetrDetector("rfdetr-small", 0.4)


# --- AppConfig.classes är en annan lista (AC 3) ---


def test_create_detector_takes_no_class_list():
    parameters = inspect.signature(model_registry.create_detector).parameters

    assert list(parameters) == ["spec", "confidence_threshold"]


def test_detection_view_does_not_pass_app_classes(qapp, tmp_path, monkeypatch):
    from xray_detector.ui.detection_view import DetectionView

    captured = []

    def create(spec, threshold):
        captured.append((spec.key, threshold))
        return FakeDetector()

    monkeypatch.setattr(model_registry, "create_detector", create)
    config = AppConfig()
    config.classes = ["cigaretter"]
    config.data_dir = tmp_path
    config.ensure_dirs()
    view = DetectionView(
        config, QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    )

    view._on_model_changed()
    view.wait_for_background()

    assert captured and captured[0][0] == view.model_combo.currentData()
    assert view.detector.class_names == ["kniv"], "klassnamnen kommer från modellen"
    assert view.config.classes == ["cigaretter"], "AppConfig.classes är datasetets etiketter"
