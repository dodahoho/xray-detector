"""Filtrering på objektklasser och datum i datasetvyn (TASK-67)."""

import pytest
from PySide6.QtCore import QDate, QSettings
from PySide6.QtWidgets import QLabel

from tests.conftest import synthetic_frame
from xray_detector.application.dataset_service import DatasetService
from xray_detector.domain.capture import StreamFrame
from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.domain.detection import Detection
from xray_detector.infrastructure.dataset_store.pending import save_pending
from xray_detector.ui.dataset_view import ALL_CLASSES, NO_MATCHES, DatasetView


def _sample(class_name: str) -> AnnotatedImage:
    return AnnotatedImage(
        synthetic_frame(60), [{"class_name": class_name, "bbox": [2, 2, 8, 8]}]
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


def _three_captures(service) -> None:
    """Pistol den 1:a, kniv den 2:a och pistol igen den 3:e."""
    service.add_samples([_sample("pistol")], captured="2026-11-01T09:00:00")
    service.add_samples([_sample("kniv")], captured="2026-11-02T09:00:00")
    service.add_samples([_sample("pistol")], captured="2026-11-03T09:00:00")


def _select_class(view, name: str) -> None:
    view.class_combo.setCurrentIndex(view.class_combo.findData(name))


def _set_range(view, first: str, last: str) -> None:
    view.date_filter.setChecked(True)
    view.date_from.setDate(QDate.fromString(first, "yyyy-MM-dd"))
    view.date_to.setDate(QDate.fromString(last, "yyyy-MM-dd"))


def _messages(view) -> list[str]:
    return [label.text() for label in view.content.findChildren(QLabel)]


def test_all_captures_are_shown_by_default(qapp, config, service, settings):
    _three_captures(service)

    view = _built(config, service, settings)

    assert view.class_combo.currentText() == ALL_CLASSES
    assert not view.date_filter.isChecked()
    assert list(view._group_headers) == [3, 2, 1]


def test_class_combo_lists_the_dataset_classes(qapp, config, service, settings):
    _three_captures(service)

    view = _built(config, service, settings)

    names = [view.class_combo.itemText(index) for index in range(view.class_combo.count())]
    assert names == [ALL_CLASSES, "pistol", "kniv"]


def test_class_filter_shows_only_captures_with_that_class(qapp, config, service, settings):
    _three_captures(service)
    view = _built(config, service, settings)

    _select_class(view, "pistol")

    assert list(view._group_headers) == [3, 1]
    assert list(view._section_headings) == ["2026-11-03", "2026-11-01"]


def test_class_filter_can_be_cleared(qapp, config, service, settings):
    _three_captures(service)
    view = _built(config, service, settings)
    _select_class(view, "kniv")
    assert list(view._group_headers) == [2]

    _select_class(view, None)

    assert list(view._group_headers) == [3, 2, 1]


def test_date_range_shows_only_captures_inside_it(qapp, config, service, settings):
    _three_captures(service)
    view = _built(config, service, settings)

    _set_range(view, "2026-11-02", "2026-11-03")

    assert list(view._group_headers) == [3, 2]
    assert list(view._section_headings) == ["2026-11-03", "2026-11-02"]


def test_date_filter_off_shows_every_date_again(qapp, config, service, settings):
    _three_captures(service)
    view = _built(config, service, settings)
    _set_range(view, "2026-11-02", "2026-11-02")
    assert list(view._group_headers) == [2]

    view.date_filter.setChecked(False)

    assert list(view._group_headers) == [3, 2, 1]


def test_class_and_date_filters_combine(qapp, config, service, settings):
    _three_captures(service)
    view = _built(config, service, settings)

    _select_class(view, "pistol")
    _set_range(view, "2026-11-01", "2026-11-02")

    assert list(view._group_headers) == [1]


def test_filter_without_matches_shows_a_message(qapp, config, service, settings):
    _three_captures(service)
    view = _built(config, service, settings)

    _set_range(view, "2026-12-01", "2026-12-31")

    assert view._group_headers == {}
    assert NO_MATCHES in _messages(view)


def test_pending_captures_are_filtered_by_class(qapp, config, tmp_path, settings):
    service = DatasetService(tmp_path / "datasets")
    service.add_samples([_sample("pistol")], captured="2026-11-01T09:00:00")
    save_pending(tmp_path, [
        StreamFrame(
            "left",
            synthetic_frame(),
            [Detection(1, 2, 30, 40, "kniv", 0.9)],
            "kamera-vanster",
        )
    ])
    view = _built(config, service, settings)
    assert "Osparade fångster" in view._section_headings

    _select_class(view, "pistol")

    assert "Osparade fångster" not in view._section_headings
    assert [thumb.pending for thumb in view._thumbs] == [False]


def test_pending_classes_are_filterable(qapp, config, tmp_path, settings):
    """En klass som bara finns i en osparad fångst går också att filtrera på."""
    service = DatasetService(tmp_path / "datasets")
    save_pending(tmp_path, [
        StreamFrame(
            "left",
            synthetic_frame(),
            [Detection(1, 2, 30, 40, "kniv", 0.9)],
            "kamera-vanster",
        )
    ])

    view = _built(config, service, settings)

    names = [view.class_combo.itemText(index) for index in range(view.class_combo.count())]
    assert names == [ALL_CLASSES, "kniv"]


def test_filtering_reuses_the_loaded_dataset(qapp, config, service, settings, monkeypatch):
    """Ombyggnaden ska inte läsa om datasetet från disk (TASK-67)."""
    _three_captures(service)
    view = _built(config, service, settings)

    def fail() -> dict:
        raise AssertionError("datasetet lästes om")

    monkeypatch.setattr(service, "load_coco", fail)

    _select_class(view, "pistol")

    assert list(view._group_headers) == [3, 1]
