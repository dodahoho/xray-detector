"""Markering och borttagning av bildpar i datasetvyn (TASK-25)."""

import numpy as np
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox

from xray_detector.application.dataset_service import DatasetService
from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.ui.dataset_view import SELECTED_BORDER, DatasetView


@pytest.fixture
def service(tmp_path) -> DatasetService:
    svc = DatasetService(tmp_path / "datasets")
    svc.add_samples([
        AnnotatedImage(np.full((30, 40, 3), 60, np.uint8),
                       [{"class_name": "kniv", "bbox": [2, 2, 8, 8]}]),
        AnnotatedImage(np.full((30, 40, 3), 120, np.uint8),
                       [{"class_name": "kniv", "bbox": [4, 4, 8, 8]}]),
    ])
    return svc


@pytest.fixture
def settings(tmp_path) -> QSettings:
    return QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)


@pytest.fixture
def view(qapp, config, service, settings) -> DatasetView:
    view = DatasetView(config, service, settings)
    view.refresh()
    view.wait_for_refresh()
    return view


def test_click_selects_whole_capture(view):
    assert len(view._thumbs) == 2

    view._on_thumb_clicked(view._thumbs[0])

    assert all(thumb.selected for thumb in view._thumbs)


def test_second_click_deselects_whole_capture(view):
    view._on_thumb_clicked(view._thumbs[0])
    view._on_thumb_clicked(view._thumbs[1])

    assert not any(thumb.selected for thumb in view._thumbs)


def test_delete_button_reflects_selection(view):
    assert not view.delete_button.isEnabled()
    assert view.delete_button.text() == "Ta &bort markerade"

    view._on_thumb_clicked(view._thumbs[0])

    assert view.delete_button.isEnabled()
    assert view.delete_button.text() == "Ta &bort markerade (1)"

    view._on_thumb_clicked(view._thumbs[0])

    assert not view.delete_button.isEnabled()
    assert view.delete_button.text() == "Ta &bort markerade"


def test_selected_capture_is_visually_marked(view):
    thumb = view._thumbs[0]
    assert SELECTED_BORDER not in thumb.styleSheet()

    view._on_thumb_clicked(thumb)

    for member in view._thumbs:
        assert SELECTED_BORDER in member.styleSheet()


def test_no_markerad_row_on_thumbnails(view):
    """Markeringen ska sitta i rubrikraden, inte som en rad per bild (TASK-29)."""
    from PySide6.QtWidgets import QLabel

    view._on_thumb_clicked(view._thumbs[0])

    for thumb in view._thumbs:
        texts = [label.text() for label in thumb.findChildren(QLabel)]
        assert not any("MARKERAD" in text for text in texts)


def test_header_is_filled_and_marked(view):
    """Rubriken behåller sin text; bara färgerna visar markeringen (TASK-68)."""
    header, frame = view._group_headers[1]
    row = header.parentWidget()
    text = header.text()
    assert text
    assert "Markerad" not in text

    view._on_thumb_clicked(view._thumbs[0])

    assert header.text() == text
    assert SELECTED_BORDER in row.styleSheet()
    assert SELECTED_BORDER in frame.styleSheet()

    view._on_thumb_clicked(view._thumbs[0])

    assert header.text() == text
    assert SELECTED_BORDER not in row.styleSheet()
    assert SELECTED_BORDER not in frame.styleSheet()


def test_delete_removes_whole_capture(view, service, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    view._on_thumb_clicked(view._thumbs[0])

    view._on_delete()
    view.wait_for_refresh()

    assert service.load_coco()["images"] == []
    assert service.load_coco()["annotations"] == []
    assert view._thumbs == []
    assert not view.delete_button.isEnabled()


def test_delete_counts_image_pairs(view, monkeypatch):
    """Dialog och statusrad räknar bildpar, inte enskilda bilder (TASK-73)."""
    asked = []

    def answer(*args, **_kwargs):
        asked.append(args[2])
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(QMessageBox, "question", staticmethod(answer))
    messages = []
    view.status_changed.connect(messages.append)
    view._on_thumb_clicked(view._thumbs[0])

    view._on_delete()
    view.wait_for_refresh()

    assert asked == [
        "Ta bort 1 bildpar med tillhörande annoteringar? Det går inte att ångra."
    ]
    assert messages == ["Tog bort 1 bildpar från datasetet"]


def test_delete_without_selection_keeps_dataset(view, service):
    messages = []
    view.status_changed.connect(messages.append)

    view._on_delete()

    assert messages == ["Markera bilder att ta bort först"]
    assert len(service.load_coco()["images"]) == 2


def test_click_selects_whole_pending_capture(qapp, config, tmp_path, settings, monkeypatch):
    from tests.conftest import synthetic_frame
    from xray_detector.domain.capture import StreamFrame
    from xray_detector.infrastructure.dataset_store.pending import save_pending

    service = DatasetService(tmp_path / "datasets")
    save_pending(tmp_path, [
        StreamFrame("left", synthetic_frame(fill=200), [], "kamera-vanster"),
        StreamFrame("right", synthetic_frame(fill=100), [], "kamera-hoger"),
    ])
    view = DatasetView(config, service, settings)
    view.refresh()
    view.wait_for_refresh()

    pending = [thumb for thumb in view._thumbs if thumb.pending]
    assert len(pending) == 2

    view._on_thumb_clicked(pending[0])

    assert all(thumb.selected for thumb in pending)
    assert view.delete_button.text() == "Ta &bort markerade (1)"

    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    view._on_delete()

    assert service.pending_captures() == []
