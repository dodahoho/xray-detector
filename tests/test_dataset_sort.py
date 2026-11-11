"""Sortering av fångsterna i datasetvyn (TASK-56)."""

import time as time_module
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QSettings

from tests.conftest import synthetic_frame
from xray_detector.application.dataset_service import DatasetService
from xray_detector.domain.capture import StreamFrame
from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.infrastructure.dataset_store import pending as pending_module
from xray_detector.infrastructure.dataset_store.pending import save_pending
from xray_detector.ui.dataset_view import DatasetView
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


def _three_captures(service) -> None:
    """Tre fångster i tidsordning: grupp 1 är äldst och grupp 3 nyast."""
    for day in (1, 2, 3):
        service.add_samples(1, [_sample()], captured=f"2026-11-0{day}T09:00:00")


def _built(service, settings) -> DatasetView:
    view = DatasetView(service, settings)
    view.refresh_versions()
    view.wait_for_refresh()
    return view


def _save_pending_at(tmp_path, monkeypatch, stamp: float) -> str:
    """Sparar en osparad fångst med given tid, så grupp-id:na blir åtskilda."""
    clock = SimpleNamespace(time=lambda: stamp, strftime=time_module.strftime)
    monkeypatch.setattr(pending_module, "time", clock)
    return save_pending(
        tmp_path, [StreamFrame("left", synthetic_frame(), [], "kamera-vanster")]
    )


def test_newest_capture_is_listed_first_by_default(qapp, service, settings):
    _three_captures(service)

    view = _built(service, settings)

    assert list(view._group_headers) == [3, 2, 1]


def test_oldest_first_setting_reverses_the_list(qapp, service, settings):
    _three_captures(service)
    settings.setValue(SORT_KEY, SORT_OLDEST)

    view = _built(service, settings)

    assert list(view._group_headers) == [1, 2, 3]


def test_changing_the_setting_rebuilds_the_list(qapp, service, settings):
    _three_captures(service)
    view = _built(service, settings)
    assert list(view._group_headers) == [3, 2, 1]

    section = view._settings_sections()[0]
    section.order_combo.setCurrentIndex(section.order_combo.findData(SORT_OLDEST))
    view.wait_for_refresh()

    assert settings.value(SORT_KEY) == SORT_OLDEST
    assert list(view._group_headers) == [1, 2, 3]


def test_pending_captures_follow_the_same_order(qapp, tmp_path, monkeypatch, settings):
    service = DatasetService(tmp_path / "datasets", ["kniv"])
    older = _save_pending_at(tmp_path, monkeypatch, 1_700_000_000.0)
    newer = _save_pending_at(tmp_path, monkeypatch, 1_700_000_100.0)

    view = _built(service, settings)
    assert list(view._group_headers) == [newer, older]

    settings.setValue(SORT_KEY, SORT_OLDEST)
    view.refresh()
    view.wait_for_refresh()

    assert list(view._group_headers) == [older, newer]
