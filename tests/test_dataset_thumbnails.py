"""Thumbnails med inritade detektioner i datasetvyn (TASK-64)."""

import pytest
from PySide6.QtCore import QSettings

from tests.conftest import synthetic_frame
from xray_detector.application.dataset_service import DatasetService
from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.ui.colors import class_color
from xray_detector.ui.dataset_view import DatasetView


def _sample(annotations: list[dict]) -> AnnotatedImage:
    return AnnotatedImage(synthetic_frame(60), annotations)


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


def _colors(pixmap, left: int = 0, top: int = 0, right: int | None = None,
            bottom: int | None = None) -> set[str]:
    """Färgerna i ett rektangulärt område av thumbnailen."""
    image = pixmap.toImage()
    right = image.width() if right is None else right
    bottom = image.height() if bottom is None else bottom
    return {
        image.pixelColor(x, y).name()
        for x in range(left, right)
        for y in range(top, bottom)
    }


def test_thumbnail_draws_the_annotations(qapp, config, service, settings):
    service.add_samples(
        [_sample([{"class_name": "pistol", "bbox": [8, 8, 24, 20]}])],
        captured="2026-11-10T09:00:00",
    )

    view = _built(config, service, settings)

    expected = class_color("pistol", ["pistol"]).name()
    assert expected in _colors(view._thumbs[0].picture.pixmap())


def test_thumbnail_draws_the_box_where_the_annotation_is(qapp, config, service, settings):
    """Ramen hamnar över objektet, inte i bildens motsatta hörn."""
    service.add_samples(
        [_sample([{"class_name": "pistol", "bbox": [2, 2, 8, 8]}])],
        captured="2026-11-10T09:00:00",
    )

    view = _built(config, service, settings)
    pixmap = view._thumbs[0].picture.pixmap()
    expected = class_color("pistol", ["pistol"]).name()

    assert expected in _colors(pixmap, 0, 0, pixmap.width() // 2, pixmap.height() // 2)
    assert expected not in _colors(
        pixmap, pixmap.width() // 2, pixmap.height() // 2, pixmap.width(), pixmap.height()
    )


def test_thumbnail_without_annotations_is_left_undrawn(qapp, config, service, settings):
    service.add_samples([_sample([])], captured="2026-11-10T09:00:00")

    view = _built(config, service, settings)

    expected = class_color("pistol", ["pistol"]).name()
    assert expected not in _colors(view._thumbs[0].picture.pixmap())
