"""Datumsektioner och kort som radbryts i datasetvyn (TASK-42)."""

import json

import numpy as np
import pytest
from PySide6.QtCore import QRect, QSettings
from PySide6.QtWidgets import QWidget

from tests.conftest import synthetic_frame
from xray_detector.application.dataset_service import DatasetService
from xray_detector.domain.capture import StreamFrame
from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.infrastructure.dataset_store.pending import save_pending
from xray_detector.ui.dataset_view import (
    UNKNOWN_DATE,
    DatasetView,
    FlowLayout,
    Thumbnail,
)
from xray_detector.ui.settings_dialog import SORT_KEY, SORT_OLDEST


def _sample(fill: int = 60) -> AnnotatedImage:
    return AnnotatedImage(
        synthetic_frame(fill), [{"class_name": "kniv", "bbox": [2, 2, 8, 8]}]
    )


@pytest.fixture
def service(tmp_path) -> DatasetService:
    return DatasetService(tmp_path / "datasets", ["kniv"])


@pytest.fixture
def settings(tmp_path) -> QSettings:
    return QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)


def _built(config, service, settings) -> DatasetView:
    view = DatasetView(config, service, settings)
    view.refresh()
    view.wait_for_refresh()
    return view


def _cards(view, title: str) -> list:
    flow = view._section_cards[title].layout()
    return [flow.itemAt(index).widget() for index in range(flow.count())]


def _images_per_row(view, title: str, width: int) -> int:
    """Lägger korten på given bredd och räknar bilderna på den fullaste raden."""
    flow = view._section_cards[title].layout()
    flow.setGeometry(QRect(0, 0, width, flow.heightForWidth(width)))
    rows: dict[int, int] = {}
    for index in range(flow.count()):
        card = flow.itemAt(index).widget()
        rows[card.y()] = rows.get(card.y(), 0) + 1
    return max(rows.values()) * 2  # varje kort har fångstens två bilder


def test_captures_are_grouped_by_capture_date(qapp, config, service, settings):
    service.add_samples([_sample()], captured="2026-11-10T09:00:00")
    service.add_samples([_sample()], captured="2026-11-10T15:00:00")
    service.add_samples([_sample()], captured="2026-11-09T09:00:00")

    view = _built(config, service, settings)

    assert list(view._section_headings) == ["2026-11-10", "2026-11-09"]
    assert len(_cards(view, "2026-11-10")) == 2
    assert len(_cards(view, "2026-11-09")) == 1


def test_each_capture_is_one_card_with_its_pair(qapp, config, service, settings):
    service.add_samples([_sample(60), _sample(120)], captured="2026-11-10T09:56:38")

    view = _built(config, service, settings)

    cards = _cards(view, "2026-11-10")
    assert len(cards) == 1
    assert len(cards[0].findChildren(Thumbnail)) == 2
    header, _frame, _base = view._group_headers[1]
    assert header.text().startswith("09:56:38")


def test_cards_wrap_and_fit_at_least_four_images_per_row(qapp, config, service, settings):
    for hour in range(4):
        service.add_samples(
            [_sample(60), _sample(120)], captured=f"2026-11-10T0{hour}:00:00"
        )

    view = _built(config, service, settings)

    assert _images_per_row(view, "2026-11-10", 1920) >= 4


def test_wide_images_still_fit_four_per_row(qapp, config, service, settings):
    """16:9-bilder ger bredare kort; fyra bilder ska rymmas även då."""
    wide = np.full((180, 320, 3), 60, np.uint8)
    for hour in range(4):
        service.add_samples(
            [
                AnnotatedImage(wide, [{"class_name": "kniv", "bbox": [2, 2, 8, 8]}]),
                AnnotatedImage(wide, [{"class_name": "kniv", "bbox": [2, 2, 8, 8]}]),
            ],
            captured=f"2026-11-10T0{hour}:00:00",
        )

    view = _built(config, service, settings)

    assert _images_per_row(view, "2026-11-10", 1920) >= 4


def test_pending_captures_get_their_own_section(qapp, config, tmp_path, settings):
    service = DatasetService(tmp_path / "datasets", ["kniv"])
    service.add_samples([_sample()], captured="2026-11-10T09:00:00")
    save_pending(tmp_path, [StreamFrame("left", synthetic_frame(), [], "kamera-vanster")])

    view = _built(config, service, settings)

    assert next(iter(view._section_headings)) == "Osparade fångster"
    assert "2026-11-10" in view._section_headings
    assert len(_cards(view, "Osparade fångster")) == 1
    assert len(_cards(view, "2026-11-10")) == 1


def test_date_sections_follow_the_sort_order(qapp, config, service, settings):
    service.add_samples([_sample()], captured="2026-11-09T09:00:00")
    service.add_samples([_sample()], captured="2026-11-10T09:00:00")

    view = _built(config, service, settings)
    assert list(view._section_headings) == ["2026-11-10", "2026-11-09"]

    settings.setValue(SORT_KEY, SORT_OLDEST)
    view.refresh()
    view.wait_for_refresh()

    assert list(view._section_headings) == ["2026-11-09", "2026-11-10"]


def test_captures_without_a_date_are_listed_last(
    qapp, config, service, settings, monkeypatch
):
    service.add_samples([_sample()], captured="2026-11-10T09:00:00")
    service.add_samples([_sample()])
    path = service.store.root / "dataset.json"
    coco = json.loads(path.read_text(encoding="utf-8"))
    for image in coco["images"]:
        if image["group"] == 2:
            image.pop("captured", None)
    path.write_text(json.dumps(coco), encoding="utf-8")
    monkeypatch.setattr("xray_detector.ui.dataset_view._mtime_timestamp", lambda path: "")

    view = _built(config, service, settings)

    assert list(view._section_headings) == ["2026-11-10", UNKNOWN_DATE]


def test_flow_layout_wraps_when_the_row_is_full(qapp):
    container = QWidget()
    flow = FlowLayout(container, spacing=10)
    boxes = []
    for _ in range(5):
        box = QWidget()
        box.setFixedSize(100, 40)
        flow.addWidget(box)
        boxes.append(box)

    width = 330
    flow.setGeometry(QRect(0, 0, width, flow.heightForWidth(width)))

    assert [box.x() for box in boxes] == [0, 110, 220, 0, 110]
    assert [box.y() for box in boxes] == [0, 0, 0, 50, 50]
    assert flow.heightForWidth(width) == 90
