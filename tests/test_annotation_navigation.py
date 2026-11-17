"""Annoteringsvyn återgår till fliken den öppnades från (TASK-60)."""

import pytest
from PySide6.QtWidgets import QMessageBox

from tests.conftest import synthetic_frame
from xray_detector.domain.capture import StreamFrame
from xray_detector.domain.config import AppConfig
from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.ui.main_window import MainWindow

# testerna startar MainWindow och tar därför sekunder (TASK-154)
pytestmark = pytest.mark.slow

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
    window.annotation_view.save()
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


# --- Avbryt och flikbyte kastar den osparade fångsten (TASK-112) ---


def answer(monkeypatch, button) -> None:
    """Svarar på osparade-ändringar-dialogen; övriga dialoger får Yes."""

    def question(parent, title, text, *args, **kwargs):
        if title == "Osparade annoteringar":
            return button
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(QMessageBox, "question", staticmethod(question))


def make_dirty(window: MainWindow) -> None:
    window.annotation_view.canvases[0]._mark_dirty()


def pending_thumbs(window: MainWindow) -> list:
    window.dataset_view.refresh()
    window.dataset_view.wait_for_refresh()
    return [thumb for thumb in window.dataset_view._thumbs if thumb.pending]


def test_cancel_removes_the_pending_capture(window):
    open_from_detection(window)
    assert window.dataset_service.pending_captures()

    window.annotation_view.cancelled.emit()

    assert window.dataset_service.pending_captures() == []
    assert pending_thumbs(window) == []


def test_cancel_keeps_the_capture_when_the_dialog_is_aborted(window, monkeypatch):
    open_from_detection(window)
    make_dirty(window)
    answer(monkeypatch, QMessageBox.StandardButton.Cancel)

    window.annotation_view.cancelled.emit()

    assert window.tabs.currentIndex() == ANNOTATION_TAB
    assert window.tabs.isTabEnabled(ANNOTATION_TAB)
    assert len(window.dataset_service.pending_captures()) == 1


def test_cancel_discards_the_changes_when_confirmed(window, monkeypatch):
    open_from_detection(window)
    make_dirty(window)
    answer(monkeypatch, QMessageBox.StandardButton.Discard)

    window.annotation_view.cancelled.emit()

    assert window.tabs.currentIndex() == DETECTION_TAB
    assert window.dataset_service.pending_captures() == []


def test_switching_tab_removes_the_pending_capture(window):
    open_from_detection(window)

    window.tabs.setCurrentIndex(DATASET_TAB)

    assert window.dataset_service.pending_captures() == []
    assert pending_thumbs(window) == []


def test_switching_tab_keeps_the_capture_when_the_dialog_is_aborted(window, monkeypatch):
    open_from_detection(window)
    make_dirty(window)
    answer(monkeypatch, QMessageBox.StandardButton.Cancel)

    window.tabs.setCurrentIndex(DATASET_TAB)

    assert window.tabs.currentIndex() == ANNOTATION_TAB
    assert len(window.dataset_service.pending_captures()) == 1


def test_switching_tab_saves_when_asked(window, monkeypatch):
    open_from_detection(window)
    make_dirty(window)
    answer(monkeypatch, QMessageBox.StandardButton.Save)

    window.tabs.setCurrentIndex(DATASET_TAB)
    window.annotation_view.wait_for_save()

    assert window.dataset_service.pending_captures() == []
    assert len(window.dataset_service.load_dataset()["images"]) == 1


def test_cancel_after_a_saved_pair_keeps_the_dataset(window):
    open_from_dataset(window)

    window.annotation_view.cancelled.emit()

    assert window.dataset_service.pending_captures() == []
    assert len(window.dataset_service.load_dataset()["images"]) == 1


def test_annotation_tab_index_is_looked_up_from_the_tab_order(window):
    """Flikindexet slås upp, så annoteringsfliken kan flyttas (TASK-127)."""
    assert window._annotation_tab == window.tabs.indexOf(window.annotation_view)

    window.tabs.removeTab(window._annotation_tab)
    window.tabs.addTab(window.annotation_view, "Annotation")

    assert window._annotation_tab == window.tabs.count() - 1
    window.tabs.setTabEnabled(window._annotation_tab, True)
    window.tabs.setCurrentIndex(window._annotation_tab)
    assert window.tabs.currentWidget() is window.annotation_view
