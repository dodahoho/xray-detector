"""Uppstartens och modelladdningens loggrader (TASK-101)."""

import logging
import os
import time

import pytest
from PySide6.QtCore import QSettings

from tests.conftest import FakeDetector
from xray_detector.application.app_config import (
    config_values,
    file_logger,
    log_path,
    setup_logging,
)
from xray_detector.domain.config import AppConfig


@pytest.fixture
def root_handlers():
    """Städar rot-loggerns handlare så testerna inte skriver i varandras filer."""
    root = logging.getLogger()
    before = list(root.handlers)
    yield
    for handler in list(root.handlers):
        if handler not in before:
            root.removeHandler(handler)
            handler.close()


def _settings(config: AppConfig) -> QSettings:
    return QSettings(str(config.data_dir / "s.ini"), QSettings.Format.IniFormat)


def test_config_values_lists_effective_values(tmp_path):
    config = AppConfig()
    config.data_dir = tmp_path
    config.logs_dir = tmp_path / "logs"
    config.default_model = "yolo26s"
    config.confidence_threshold = 0.55

    text = config_values(config)

    assert "yolo26s" in text
    assert "0.55" in text
    assert str(tmp_path / "logs") in text
    assert "kniv" in text


def test_log_format_contains_process_id(tmp_path, root_handlers):
    log = setup_logging(tmp_path / "logs")
    log.info("process-id-rad 123")
    training = file_logger("xray.test.training", log_path(tmp_path / "logs", "training"))
    training.info("process-id-rad 456")

    for handler in logging.getLogger().handlers + training.handlers:
        handler.flush()
    app_log = (tmp_path / "logs" / "app.log").read_text(encoding="utf-8")
    training_log = (tmp_path / "logs" / "training.log").read_text(encoding="utf-8")
    assert f"[{os.getpid()}] INFO xray: process-id-rad 123" in app_log
    assert f"[{os.getpid()}] INFO xray.test.training: process-id-rad 456" in training_log


def test_startup_logs_config_file_and_values(tmp_path, caplog):
    from xray_detector.app import _log_startup

    config = AppConfig()
    config.default_model = "yolo26s"
    config_file = tmp_path / "config.yaml"

    with caplog.at_level(logging.INFO, logger="xray"):
        _log_startup(config, config_file, logging.getLogger("xray"))

    assert str(config_file) in caplog.text
    assert "yolo26s" in caplog.text


def test_startup_logs_default_when_no_config_file(caplog):
    from xray_detector.app import _log_startup

    with caplog.at_level(logging.INFO, logger="xray"):
        _log_startup(AppConfig(), None, logging.getLogger("xray"))

    assert "konfig: default" in caplog.text


def test_model_load_logs_weights_family_device_and_time(qapp, config, caplog):
    from xray_detector.application.model_registry import ModelSpec
    from xray_detector.ui.detection_view import DetectionView

    view = DetectionView(config, _settings(config))
    view._loading_spec = ModelSpec(
        key="yolo26m",
        label="YOLO26m",
        family="yolo",
        weights=str(config.models_dir / "yolo26m.pt"),
    )
    view._model_started = time.monotonic() - 1.5
    detector = FakeDetector()
    detector.device_label = "CUDA (Test-GPU)"

    with caplog.at_level(logging.INFO, logger="xray"):
        view._on_model_loaded(detector)

    assert "yolo26m.pt" in caplog.text
    assert "familj=yolo" in caplog.text
    assert "enhet=CUDA (Test-GPU)" in caplog.text
    assert "1.5 s" in caplog.text


def test_startup_logs_dataset_size(qapp, config, caplog, monkeypatch):
    from xray_detector.ui.detection_view import DetectionView
    from xray_detector.ui.main_window import MainWindow

    monkeypatch.setattr(DetectionView, "check_device", lambda self: None)
    with caplog.at_level(logging.INFO, logger="xray"):
        MainWindow(config)

    assert "Dataset: 0 bildpar" in caplog.text


def test_startup_logs_camera_enumeration(qapp, config, caplog, monkeypatch):
    from xray_detector.infrastructure.video.devices import DeviceInfo
    from xray_detector.ui.detection_view import DetectionView

    monkeypatch.setattr(
        "xray_detector.application.video_service.list_devices",
        lambda: [DeviceInfo(0, "UVC-kamera 1"), DeviceInfo(1, "UVC-kamera 2")],
    )
    with caplog.at_level(logging.INFO, logger="xray"):
        DetectionView(config, _settings(config))

    assert "Kameror: 0=UVC-kamera 1, 1=UVC-kamera 2" in caplog.text
