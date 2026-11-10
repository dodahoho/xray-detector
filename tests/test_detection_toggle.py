"""Av/på-knapp för objektdetektion i detektionsvyn (TASK-38)."""

import pytest
from PySide6.QtCore import QSettings

from tests.conftest import FakeDetector, synthetic_frame
from xray_detector.application import model_registry
from xray_detector.domain.capture import StreamFrame
from xray_detector.domain.config import AppConfig
from xray_detector.domain.detection import Detection
from xray_detector.ui.detection_view import (
    DETECTION_TURN_OFF,
    DETECTION_TURN_ON,
    DetectionView,
)


@pytest.fixture
def view(qapp, tmp_path, monkeypatch) -> DetectionView:
    calls = []
    original = model_registry.create_detector

    def counting(spec, class_names, threshold):
        calls.append(spec.key)
        return original(spec, class_names, threshold)

    monkeypatch.setattr(model_registry, "create_detector", counting)
    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    view = DetectionView(
        config, QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    )
    view._create_calls = calls
    view._detector_calls = []
    view.video_service.set_detector = view._detector_calls.append
    return view


def test_toggle_button_is_last_in_header_row(view):
    bar = view.layout().itemAt(0).layout()

    assert bar.itemAt(bar.count() - 1).widget() is view.detection_button
    assert view.detection_button.isCheckable()
    assert view.detection_button.isChecked()
    # texten säger vad ett klick gör: detektionen är igång vid start
    assert view.detection_button.text() == DETECTION_TURN_OFF


def test_toggle_off_detaches_detector_without_reloading(view):
    detector = FakeDetector()
    view.detector = detector
    view._create_calls.clear()
    view._detector_calls.clear()

    view.detection_button.setChecked(False)

    assert view.detection_enabled is False
    assert view.detector is detector, "modellen ska vara kvar för snabb återstart"
    assert view._detector_calls == [None]
    assert view._create_calls == []
    assert view.detection_button.text() == DETECTION_TURN_ON


def test_toggle_off_clears_overlay(view):
    frame = StreamFrame(
        "left",
        synthetic_frame(),
        [Detection(2, 2, 20, 20, "kniv", 0.9)],
        "kamera",
    )
    view.left.show_frame(frame)
    assert view.left.latest.detections

    view.detection_button.setChecked(False)

    assert view.left.latest.detections == []


def test_toggle_on_reattaches_same_detector(view):
    detector = FakeDetector()
    view.detector = detector
    view.detection_button.setChecked(False)
    view._create_calls.clear()
    view._detector_calls.clear()

    view.detection_button.setChecked(True)

    assert view.detection_enabled is True
    assert view._detector_calls == [detector]
    assert view._create_calls == []
    assert view.detection_button.text() == DETECTION_TURN_OFF


def test_toggle_on_without_detector_loads_model(view, monkeypatch):
    view.detector = None
    view.detection_button.setChecked(False)
    rebuilt = []
    monkeypatch.setattr(view, "_on_model_changed", lambda: rebuilt.append(True))

    view.detection_button.setChecked(True)

    assert rebuilt == [True]


def _unstarted_worker(view, monkeypatch, tmp_path):
    """StreamWorker som aldrig startas: signaler och set_detector går att koppla."""
    from xray_detector.infrastructure.video.camera_service import StreamWorker
    from xray_detector.infrastructure.video.source import FileSource

    worker = StreamWorker("left", FileSource(tmp_path / "saknas.mp4"))
    attached = []
    monkeypatch.setattr(worker, "set_detector", attached.append)
    monkeypatch.setattr(view.video_service, "set_source", lambda *args: worker)
    return attached


def test_new_source_gets_no_detector_when_disabled(view, monkeypatch, tmp_path):
    attached = _unstarted_worker(view, monkeypatch, tmp_path)
    view.detector = FakeDetector()
    view.detection_button.setChecked(False)

    view._on_source_requested("left", "file", tmp_path / "saknas.mp4")

    assert attached == [None]


def test_new_source_gets_detector_when_enabled(view, monkeypatch, tmp_path):
    attached = _unstarted_worker(view, monkeypatch, tmp_path)
    view.detector = FakeDetector()

    view._on_source_requested("left", "file", tmp_path / "saknas.mp4")

    assert attached == [view.detector]


def test_resume_after_training_keeps_detection_off(view, monkeypatch):
    view.detector = FakeDetector()
    view.detection_button.setChecked(False)
    view.pause_detection()
    rebuilt = []
    monkeypatch.setattr(view, "_on_model_changed", lambda: rebuilt.append(True))
    view._detector_calls.clear()

    view.resume_detection()

    assert rebuilt == [], "avstängd detektion ska inte ladda modellen efter träning"
    assert view._detector_calls == []
