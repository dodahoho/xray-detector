"""Annoteringsvyn återgår till fliken den öppnades från (TASK-60)."""

import pytest
from PySide6.QtWidgets import QMessageBox

from tests.conftest import synthetic_frame
from xray_detector.domain.capture import StreamFrame
from xray_detector.domain.config import AppConfig
from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.ui.main_window import MainWindow

DETECTION_TAB = 0
ANNOTATION_TAB = 1
DATASET_TAB = 2


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
    window.dataset_service.add_samples([AnnotatedImage(synthetic_frame(), [
        {"class_name": "kniv", "bbox": [8, 8, 20, 24]}
    ])])
    window.dataset_view.refresh()
    window.dataset_view.wait_for_refresh()
    window.dataset_view._on_thumb_double_clicked(window.dataset_view._thumbs[0])


def save(window: MainWindow) -> None:
    window.annotation_view._on_save()
    window.annotation_view.wait_for_save()


def test_capture_from_detection_returns_to_detection_on_cancel(window):
    open_from_detection(window)
    assert window.tabs.currentIndex() == ANNOTATION_TAB

    window.annotation_view.cancelled.emit()

    assert window.tabs.currentIndex() == DETECTION_TAB
    assert not window.tabs.isTabEnabled(ANNOTATION_TAB)


def test_capture_from_detection_returns_to_detection_on_save(window):
    open_from_detection(window)
    assert window.tabs.currentIndex() == ANNOTATION_TAB

    save(window)

    assert window.tabs.currentIndex() == DETECTION_TAB
    assert not window.tabs.isTabEnabled(ANNOTATION_TAB)


def test_open_from_dataset_returns_to_dataset_on_cancel(window):
    open_from_dataset(window)
    assert window.tabs.currentIndex() == ANNOTATION_TAB

    window.annotation_view.cancelled.emit()

    assert window.tabs.currentIndex() == DATASET_TAB
    assert not window.tabs.isTabEnabled(ANNOTATION_TAB)


def test_open_from_dataset_returns_to_dataset_on_save(window):
    open_from_dataset(window)
    assert window.tabs.currentIndex() == ANNOTATION_TAB

    save(window)

    assert window.tabs.currentIndex() == DATASET_TAB
    assert not window.tabs.isTabEnabled(ANNOTATION_TAB)
