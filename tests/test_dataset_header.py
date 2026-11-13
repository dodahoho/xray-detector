"""Tidsstämpel i datasetvyns rubrikrad (TASK-30)."""

import json
import os
from datetime import datetime

import numpy as np
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QLabel, QMessageBox

from tests.conftest import synthetic_frame
from xray_detector.application.dataset_service import DatasetService
from xray_detector.domain.capture import StreamFrame
from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.infrastructure.dataset_store.pending import (
    pending_saved_at,
    save_pending,
)
from xray_detector.ui.dataset_view import DatasetView, Thumbnail


def _sample(fill: int = 60) -> AnnotatedImage:
    return AnnotatedImage(
        np.full((30, 40, 3), fill, np.uint8),
        [{"class_name": "kniv", "bbox": [2, 2, 8, 8]}],
    )


@pytest.fixture
def service(tmp_path) -> DatasetService:
    return DatasetService(tmp_path / "datasets")


@pytest.fixture
def settings(tmp_path) -> QSettings:
    return QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)


def _header_text(view, group_id) -> str:
    header, _frame = view._group_headers[group_id]
    return header.text()


def test_add_samples_records_capture_time(service):
    service.add_samples([_sample()], captured="2026-11-10T09:56:38")

    images = service.load_dataset()["images"]
    assert images[0]["captured"] == "2026-11-10T09:56:38"


def test_header_shows_capture_time(qapp, config, service, settings):
    service.add_samples([_sample(60), _sample(120)], captured="2026-11-10T09:56:38")
    view = DatasetView(config, service, settings)
    view.refresh()
    view.wait_for_refresh()

    # datumet är sektionens rubrik, kortet visar fångstens tid (TASK-42)
    assert "2026-11-10" in view._section_headings
    assert _header_text(view, 1) == "09:56:38"


def test_header_lists_the_classes_as_badges(qapp, config, service, settings):
    """Titelraden räknar upp klasserna som märken, utan antal (TASK-66)."""
    service.add_samples(
        [
            AnnotatedImage(
                np.full((30, 40, 3), 60, np.uint8),
                [
                    {"class_name": "pistol", "bbox": [2, 2, 8, 8]},
                    {"class_name": "kniv", "bbox": [4, 4, 8, 8]},
                ],
            ),
            AnnotatedImage(
                np.full((30, 40, 3), 120, np.uint8),
                [{"class_name": "pistol", "bbox": [2, 2, 8, 8]}],
            ),
        ],
        captured="2026-11-10T09:56:38",
    )
    view = DatasetView(config, service, settings)
    view.refresh()
    view.wait_for_refresh()

    header, _frame = view._group_headers[1]
    texts = [label.text() for label in header.parentWidget().findChildren(QLabel)]
    assert texts == ["09:56:38", "kniv", "pistol"]


def test_badges_follow_the_time_with_extra_air(qapp, config, service, settings):
    """Ingen plats reserveras för 'Markerad'; märkena får luft mot tiden men sitter tätt (TASK-68)."""
    service.add_samples(
        [
            AnnotatedImage(
                np.full((30, 40, 3), 60, np.uint8),
                [
                    {"class_name": "pistol", "bbox": [2, 2, 8, 8]},
                    {"class_name": "kniv", "bbox": [4, 4, 8, 8]},
                ],
            ),
            AnnotatedImage(
                np.full((30, 40, 3), 120, np.uint8),
                [{"class_name": "pistol", "bbox": [2, 2, 8, 8]}],
            ),
        ],
        captured="2026-11-10T09:56:38",
    )
    view = DatasetView(config, service, settings)
    view.refresh()
    view.wait_for_refresh()

    header, _frame = view._group_headers[1]
    row = header.parentWidget()
    row.resize(400, 24)
    row.layout().activate()
    kniv, pistol = [label for label in row.findChildren(QLabel) if label is not header]

    assert header.width() == header.sizeHint().width()
    time_to_badge = kniv.x() - (header.x() + header.width())
    badge_to_badge = pistol.x() - (kniv.x() + kniv.width())
    assert time_to_badge > badge_to_badge


def test_card_has_only_a_title_row_and_thumbnails(qapp, config, service, settings):
    """Bildtexten under thumbnails är borta (TASK-66)."""
    service.add_samples([_sample(60), _sample(120)], captured="2026-11-10T09:56:38")
    view = DatasetView(config, service, settings)
    view.refresh()
    view.wait_for_refresh()

    card = view._group_headers[1][1]
    thumbs = card.findChildren(Thumbnail)
    assert len(thumbs) == 2
    for thumb in thumbs:
        assert thumb.findChildren(QLabel) == [thumb.picture]


def test_header_falls_back_to_file_mtime(qapp, config, service, settings):
    """Äldre dataset saknar 'captured': då används bildfilens tidsstämpel."""
    service.add_samples([_sample()])
    path = service.store.root / "dataset.json"
    metadata = json.loads(path.read_text(encoding="utf-8"))
    for image in metadata["images"]:
        image.pop("captured", None)
    path.write_text(json.dumps(metadata), encoding="utf-8")

    stamp = datetime(2026, 5, 4, 12, 30, 15).timestamp()
    image_path = service.images_dir / metadata["images"][0]["file_name"]
    os.utime(image_path, (stamp, stamp))

    view = DatasetView(config, service, settings)
    view.refresh()
    view.wait_for_refresh()

    expected = datetime.fromtimestamp(stamp)
    assert expected.strftime("%Y-%m-%d") in view._section_headings
    assert _header_text(view, 1).startswith(expected.strftime("%H:%M:%S"))


def test_pending_header_shows_saved_at(qapp, config, tmp_path, settings):
    service = DatasetService(tmp_path / "datasets")
    group_id = save_pending(tmp_path, [
        StreamFrame("left", synthetic_frame(fill=200), [], "kamera-vanster"),
        StreamFrame("right", synthetic_frame(fill=100), [], "kamera-hoger"),
    ])
    view = DatasetView(config, service, settings)
    view.refresh()
    view.wait_for_refresh()

    saved_at = pending_saved_at(tmp_path, group_id)
    assert saved_at
    assert _header_text(view, group_id).startswith(f"Osparad · {saved_at.replace('T', ' ')}")


def test_saved_capture_keeps_pending_timestamp(qapp, tmp_path, monkeypatch):
    """Tiden ska vara när bilderna fångades, inte när annoteringen sparades."""
    from xray_detector.domain.config import AppConfig
    from xray_detector.ui.main_window import MainWindow

    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    window = MainWindow(config)
    window._on_capture([
        StreamFrame("left", synthetic_frame(fill=200), [], "kamera-vanster"),
        StreamFrame("right", synthetic_frame(fill=100), [], "kamera-hoger"),
    ])
    group_id = window.annotation_view.pending_group_id
    saved_at = pending_saved_at(tmp_path, group_id)
    assert saved_at

    window.annotation_view._on_save()
    window.annotation_view.wait_for_save()

    images = window.dataset_service.load_dataset()["images"]
    assert images
    assert all(image["captured"] == saved_at for image in images)
