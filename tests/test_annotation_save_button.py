"""Spara till dataset kräver en ändring när bilderna redan finns i datasetet (TASK-62)."""

import pytest
from PySide6.QtWidgets import QMessageBox

from tests.conftest import synthetic_frame
from xray_detector.domain.capture import StreamFrame
from xray_detector.domain.config import AppConfig
from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.ui.main_window import MainWindow


@pytest.fixture(autouse=True)
def quiet_dialogs(monkeypatch):
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))


@pytest.fixture
def window(qapp, tmp_path) -> MainWindow:
    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    return MainWindow(config)


def frames() -> list[StreamFrame]:
    return [StreamFrame("left", synthetic_frame(), [], "kamera")]


def open_from_detection(window: MainWindow) -> None:
    window.detection_view.capture_requested.emit(frames())


def open_from_dataset(window: MainWindow) -> None:
    """Dubbelklick på en fångst som redan ligger i datasetet."""
    window.dataset_service.add_samples([AnnotatedImage(synthetic_frame(), [
        {"class_name": "kniv", "bbox": [8, 8, 20, 24]}
    ])])
    window.dataset_view.refresh()
    window.dataset_view.wait_for_refresh()
    window.dataset_view._on_thumb_double_clicked(window.dataset_view._thumbs[0])


def open_pending_from_dataset(window: MainWindow) -> None:
    """Dubbelklick på en osparad fångst i datasetvyn."""
    window.dataset_service.save_pending(frames())
    window.dataset_view.refresh()
    window.dataset_view.wait_for_refresh()
    thumb = next(t for t in window.dataset_view._thumbs if t.pending)
    window.dataset_view._on_thumb_double_clicked(thumb)


def test_save_is_enabled_for_a_new_capture(window):
    open_from_detection(window)

    assert window.annotation_view.save_button.isEnabled()


def test_save_is_disabled_for_images_already_in_the_dataset(window):
    open_from_dataset(window)

    assert not window.annotation_view.save_button.isEnabled()


def test_save_is_enabled_for_an_unsaved_capture_from_the_dataset(window):
    open_pending_from_dataset(window)

    assert window.annotation_view.save_button.isEnabled()


def test_deleting_a_box_enables_save(window):
    open_from_dataset(window)
    canvas = window.annotation_view.canvases[0]
    canvas.selected = canvas.rects[0]

    canvas.delete_selected()

    assert window.annotation_view.save_button.isEnabled()


def test_save_is_disabled_again_when_the_change_is_discarded(window):
    open_from_dataset(window)
    window.annotation_view.canvases[0]._mark_dirty()

    window.annotation_view.mark_clean()

    assert not window.annotation_view.save_button.isEnabled()


def test_save_is_enabled_again_for_the_next_capture(window):
    open_from_dataset(window)

    open_from_detection(window)

    assert window.annotation_view.save_button.isEnabled()
