"""Tröskelbyte utan omladdning och RF-DETR-optimering (TASK-36)."""

import sys
import types

import pytest
import torch
from PySide6.QtCore import QSettings

from tests.conftest import FakeDetector
from xray_detector.application import model_registry
from xray_detector.domain.config import AppConfig
from xray_detector.ui.detection_view import DetectionView


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
    view = DetectionView(config, QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
    view._create_calls = calls
    return view


def test_threshold_change_updates_detector_without_reload(view):
    view.detector = FakeDetector()
    view._create_calls.clear()

    view.conf_spin.setValue(0.55)

    assert view.detector.confidence_threshold == 0.55
    assert view._create_calls == []


def test_threshold_change_without_detector_is_harmless(view):
    view.detector = None
    view._create_calls.clear()

    view.conf_spin.setValue(0.6)

    assert view._create_calls == []


def test_base_detector_threshold_setter():
    detector = FakeDetector()

    detector.set_confidence_threshold(0.7)

    assert detector.confidence_threshold == 0.7


def _fake_rfdetr(monkeypatch, calls):
    class _FakeModel:
        def inference(self, **kwargs):
            calls.append(kwargs)

    fake = types.ModuleType("rfdetr")
    fake.RFDETRSmall = _FakeModel
    monkeypatch.setitem(sys.modules, "rfdetr", fake)


def test_rfdetr_optimizes_for_inference_on_cuda(monkeypatch):
    calls = []
    _fake_rfdetr(monkeypatch, calls)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)

    from xray_detector.infrastructure.detectors.rfdetr_detector import RfDetrDetector

    RfDetrDetector("rfdetr-small", ["kniv"], 0.4)

    assert calls and calls[0]["dtype"] is torch.float16


def test_rfdetr_skips_optimization_without_cuda(monkeypatch):
    calls = []
    _fake_rfdetr(monkeypatch, calls)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)

    from xray_detector.infrastructure.detectors.rfdetr_detector import RfDetrDetector

    RfDetrDetector("rfdetr-small", ["kniv"], 0.4)

    assert calls == []
