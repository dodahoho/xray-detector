"""Hela kortet markerar fångsten i datasetvyn (TASK-65)."""

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest

from tests.conftest import synthetic_frame
from xray_detector.application.dataset_service import DatasetService
from xray_detector.domain.capture import StreamFrame
from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.infrastructure.dataset_store.pending import save_pending
from xray_detector.ui.dataset_view import CaptureCard, DatasetView, Thumbnail


def _sample(fill: int = 60) -> AnnotatedImage:
    return AnnotatedImage(
        synthetic_frame(fill), [{"class_name": "kniv", "bbox": [2, 2, 8, 8]}]
    )


@pytest.fixture
def service(tmp_path) -> DatasetService:
    return DatasetService(tmp_path / "datasets")


@pytest.fixture
def settings(tmp_path) -> QSettings:
    return QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)


def _built(config, service, settings) -> DatasetView:
    view = DatasetView(config, service, settings)
    view.refresh()
    view.wait_for_refresh()
    return view


def _card(view, group_id) -> CaptureCard:
    return view._group_headers[group_id][1]


def test_click_on_the_card_selects_the_whole_capture(qapp, config, service, settings):
    service.add_samples([_sample(60), _sample(120)], captured="2026-11-10T09:00:00")
    view = _built(config, service, settings)

    QTest.mouseClick(_card(view, 1), Qt.MouseButton.LeftButton)

    assert all(thumb.selected for thumb in view._thumbs)
    assert view.delete_button.text() == "Ta &bort markerade (2)"


def test_second_click_on_the_card_deselects(qapp, config, service, settings):
    service.add_samples([_sample(60), _sample(120)], captured="2026-11-10T09:00:00")
    view = _built(config, service, settings)

    QTest.mouseClick(_card(view, 1), Qt.MouseButton.LeftButton)
    QTest.mouseClick(_card(view, 1), Qt.MouseButton.LeftButton)

    assert not any(thumb.selected for thumb in view._thumbs)


def test_click_on_a_thumbnail_toggles_only_once(qapp, config, service, settings):
    """Thumbnailens eget klick får inte också nå kortet bakom (TASK-65)."""
    service.add_samples([_sample(60), _sample(120)], captured="2026-11-10T09:00:00")
    view = _built(config, service, settings)

    QTest.mouseClick(view._thumbs[0], Qt.MouseButton.LeftButton)

    assert all(thumb.selected for thumb in view._thumbs)


def test_click_on_the_header_selects_the_capture(qapp, config, service, settings):
    """Rubriken är genomsläpplig, så klicket når kortet (TASK-65)."""
    service.add_samples([_sample(60), _sample(120)], captured="2026-11-10T09:00:00")
    view = _built(config, service, settings)
    header = view._group_headers[1][0]

    QTest.mouseClick(header, Qt.MouseButton.LeftButton)

    assert all(thumb.selected for thumb in view._thumbs)


def test_click_on_a_pending_card_selects_the_capture(qapp, config, tmp_path, settings):
    service = DatasetService(tmp_path / "datasets")
    save_pending(tmp_path, [
        StreamFrame("left", synthetic_frame(fill=200), [], "kamera-vanster"),
        StreamFrame("right", synthetic_frame(fill=100), [], "kamera-hoger"),
    ])
    view = _built(config, service, settings)
    group_id = next(iter(view._pending_by_group))

    QTest.mouseClick(_card(view, group_id), Qt.MouseButton.LeftButton)

    pending = [thumb for thumb in view._thumbs if thumb.pending]
    assert len(pending) == 2
    assert all(thumb.selected for thumb in pending)


def test_card_click_keeps_the_card_size(qapp, config, service, settings):
    """Markering via kortet får inte heller ändra kortets storlek (TASK-63)."""
    service.add_samples([_sample(60), _sample(120)], captured="2026-11-10T09:00:00")
    view = _built(config, service, settings)
    card = _card(view, 1)
    before = (card.geometry(), card.sizeHint())

    QTest.mouseClick(card, Qt.MouseButton.LeftButton)

    assert (card.geometry(), card.sizeHint()) == before


def test_thumbnails_still_open_the_annotation_on_double_click(
    qapp, config, service, settings
):
    service.add_samples([_sample(60), _sample(120)], captured="2026-11-10T09:00:00")
    view = _built(config, service, settings)
    opened = []
    view.open_annotation_requested.connect(opened.append)

    QTest.mouseDClick(view._thumbs[0], Qt.MouseButton.LeftButton)

    assert len(opened) == 1
    assert len(opened[0]) == 2
    assert all(isinstance(thumb, Thumbnail) for thumb in view._thumbs)
