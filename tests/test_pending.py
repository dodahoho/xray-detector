"""Kraschsäker pending-kö (TASK-12)."""

import numpy as np
from PySide6.QtWidgets import QMessageBox

from tests.conftest import synthetic_frame
from xray_detector.domain.capture import StreamFrame
from xray_detector.domain.detection import Detection
from xray_detector.infrastructure.dataset_store.pending import (
    list_pending,
    remove_pending,
    save_pending,
)


def frames_two():
    return [
        StreamFrame("left", synthetic_frame(fill=200),
                    [Detection(1, 2, 30, 40, "kniv", 0.9)], "kamera-vanster"),
        StreamFrame("right", synthetic_frame(fill=100), [], "kamera-hoger"),
    ]


def test_save_and_list_pending_roundtrip(tmp_path):
    group_id = save_pending(tmp_path, frames_two())
    assert group_id
    captures = list_pending(tmp_path)
    assert len(captures) == 1
    capture = captures[0]
    assert capture.group_id == group_id
    assert len(capture.frames) == 2
    assert capture.frames[0].source_id == "left"
    assert capture.frames[0].detections[0].class_name == "kniv"
    assert capture.frames[0].detections[0].confidence == 0.9
    assert capture.frames[1].detections == []
    assert capture.frames[0].frame.shape == (48, 64, 3)
    assert capture.frames[0].frame[0, 0, 0] == 200  # BGR-vardet bevarat genom PNG


def test_remove_pending(tmp_path):
    group_id = save_pending(tmp_path, frames_two())
    remove_pending(tmp_path, group_id)
    assert list_pending(tmp_path) == []
    remove_pending(tmp_path, "finns-inte")  # far inte kasta


def test_pending_survives_restart_and_can_be_annotated(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    monkeypatch.setattr(QMessageBox, "information",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok))
    from xray_detector.domain.config import AppConfig
    from xray_detector.ui.main_window import MainWindow

    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()

    # fangst -> pending skrivs direkt, annotering avbryts (som vid krasch)
    window = MainWindow(config)
    window._on_capture(frames_two())
    assert window.dataset_service.pending_captures()
    window.annotation_view.cancelled.emit()

    # "omstart": ny MainWindow ser den osparade fangsten
    window2 = MainWindow(config)
    view = window2.dataset_view
    view.refresh()
    view.wait_for_refresh()
    pending = view._pending_by_group
    assert len(pending) == 1
    pending_thumb = next(t for t in view._thumbs if t.pending)
    # bildtexten är borta; källan ligger i tooltipen och "Osparad" i titelraden (TASK-66)
    assert "kamera-vanster" in pending_thumb.toolTip()
    header, _frame, _base = view._group_headers[pending_thumb.group_id]
    assert header.text().startswith("Osparad")

    # dubbelklick ateroppnar i annotering och sparning tar bort pending
    view._on_thumb_double_clicked(pending_thumb)
    assert window2.annotation_view.canvases[0].image is not None
    assert window2.annotation_view.pending_group_id == pending_thumb.group_id
    window2.annotation_view._on_save()
    window2.annotation_view.wait_for_save()
    assert window2.dataset_service.pending_captures() == []
    view.refresh()
    view.wait_for_refresh()
    assert not any(t.pending for t in view._thumbs)
    # datan hamnade i datasetet
    assert window2.dataset_service.metadata()["num_images"] >= 1


def test_pending_can_be_deleted_from_view(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    from xray_detector.domain.config import AppConfig
    from xray_detector.ui.main_window import MainWindow

    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    window = MainWindow(config)
    window._on_capture(frames_two())
    window.dataset_view.refresh()
    window.dataset_view.wait_for_refresh()
    thumb = next(t for t in window.dataset_view._thumbs if t.pending)
    thumb.set_selected(True)
    window.dataset_view._on_delete()
    assert window.dataset_service.pending_captures() == []
