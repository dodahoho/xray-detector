from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from xray_detector.models import Detection
from xray_detector.ui.annotation_view import AnnotationView


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_annotation_view_loads_detections_and_saves(store, capture_factory) -> None:
    app = _app()
    capture = capture_factory(0)
    view = AnnotationView(store)
    view.load_capture(capture, [])

    assert set(view.canvases) == {"left", "right"}
    left = view.canvases["left"]
    assert len(left.boxes()) == 1
    existing = left.boxes()[0].to_detection()
    assert existing.class_name == "skruv"

    item = left.add_detection(Detection(55, 10, 90, 60, 0, "mutter", 1.0))
    item.setSelected(True)
    view.class_combo.setCurrentText("bricka")
    assert item.class_name == "bricka"

    view._save()
    dataset, metadata = store.load()
    assert len(dataset.images) == 2
    assert len(dataset.annotations) == 2
    assert "bricka" in metadata.categories
    assert view.capture is None
    view.deleteLater()
    app.processEvents()
