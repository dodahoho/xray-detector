from __future__ import annotations

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from xray_detector.application.dataset_service import DatasetService
from xray_detector.config import AppConfig
from xray_detector.domain.detection import BBox, CaptureSnapshot, Detection
from xray_detector.ui.views.annotation_view import AnnotationView


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


def _snapshot() -> CaptureSnapshot:
    frame = np.zeros((120, 160, 3), dtype=np.uint8)
    detection = Detection(BBox(10, 10, 60, 60), 0.8, 0, "part")
    return CaptureSnapshot(
        frames={"cam0": frame.copy(), "cam1": frame.copy()},
        detections={"cam0": [detection], "cam1": [detection]},
        sequences={"cam0": 1, "cam1": 1},
        captured_at="2026-01-01T00:00:00+00:00",
        pair_id="pair-ui",
    )


def test_annotation_view_loads_and_saves(qt_app, tmp_path):
    config = AppConfig.load(tmp_path / "config.yaml")
    config.app.data_root = str(tmp_path / "data")
    config.ensure_dirs()
    service = DatasetService(config)

    view = AnnotationView(_snapshot(), config, service, ["part", "defect"])
    assert len(view.canvas0.annotations()) == 1
    assert len(view.canvas1.annotations()) == 1
    assert view.canvas0.annotations()[0].class_name == "part"

    saved = []
    view.saved.connect(saved.append)
    view.save()

    assert saved
    assert saved[0].version == "v000001"
    assert saved[0].annotation_count == 2
    assert service.latest_version() == "v000001"
    view.deleteLater()


def test_annotation_canvas_can_delete_box(qt_app, tmp_path):
    config = AppConfig.load(tmp_path / "config.yaml")
    config.app.data_root = str(tmp_path / "data")
    service = DatasetService(config)
    view = AnnotationView(_snapshot(), config, service, ["part"])
    box = view.canvas0.selected_box()
    assert box is None
    item = [i for i in view.canvas0._scene.items() if hasattr(i, "to_annotation")][0]
    item.setSelected(True)
    assert view.canvas0.delete_selected()
    assert view.canvas0.annotations() == []
    view.deleteLater()


def test_detection_pipeline_captures_with_fake_model(qt_app, tmp_path):
    import time

    from xray_detector.infrastructure.detectors.base import FakeDetector
    from xray_detector.infrastructure.video.source import SourceSpec
    from xray_detector.ui.pipeline import DetectionPipeline

    config = AppConfig.load(tmp_path / "config.yaml")
    config.app.data_root = str(tmp_path / "data")
    config.detection.max_fps = 30
    pipeline = DetectionPipeline(config)
    specs = {
        "cam0": SourceSpec(role="cam0", type="test_pattern", width=320, height=240, fps=30),
        "cam1": SourceSpec(role="cam1", type="test_pattern", width=320, height=240, fps=30),
    }
    pipeline.start(specs, FakeDetector(class_name="part"))
    try:
        snapshot = None
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            qt_app.processEvents()
            try:
                snapshot = pipeline.capture()
                if all(snapshot.detections.get(role) for role in ("cam0", "cam1")):
                    break
            except RuntimeError:
                pass
            time.sleep(0.05)
        assert snapshot is not None
        assert snapshot.frames["cam0"].shape == (240, 320, 3)
        assert snapshot.detections["cam0"][0].class_name == "part"
        assert snapshot.detections["cam1"][0].class_name == "part"
    finally:
        pipeline.stop()
