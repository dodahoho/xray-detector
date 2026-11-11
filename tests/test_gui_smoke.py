"""GUI-smoke: hela flödet datasetvy -> annotering -> spara utan kamera."""

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox

from tests.conftest import synthetic_frame
from xray_detector.application.dataset_service import DatasetService
from xray_detector.domain.capture import StreamFrame
from xray_detector.domain.config import AppConfig
from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.ui.main_window import MainWindow
from xray_detector.ui.settings_dialog import ThemeSection
from xray_detector.ui.theme import current_theme


@pytest.fixture(autouse=True)
def quiet_dialogs(monkeypatch):
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    monkeypatch.setattr(QMessageBox, "information",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok))


@pytest.fixture
def app_config(tmp_path) -> AppConfig:
    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    return config


def test_gui_capture_annotate_save_roundtrip(qapp, app_config):
    service = DatasetService(app_config.dataset_dir, app_config.classes)
    service.add_samples(1, [AnnotatedImage(synthetic_frame(), [
        {"class_name": "kniv", "bbox": [8, 8, 20, 24]}
    ])])

    window = MainWindow(app_config)
    view = window.dataset_view
    view.refresh_versions()
    view.wait_for_refresh()
    assert view.version_combo.currentData() == 1
    assert len(view._thumbs) == 1

    # dubbelklicka -> annoteringsvy med rektangeln inladdad
    view._on_thumb_double_clicked(view._thumbs[0])
    canvas = window.annotation_view.canvases[0]
    assert canvas.image is not None
    assert [rect.class_name for rect in canvas.rects] == ["kniv"]
    assert window.tabs.currentIndex() == 1

    # spara -> ny fångstgrupp i samma version
    window.annotation_view._on_save()
    window.annotation_view.wait_for_save()
    coco = service.load_coco(1)
    assert len(coco["images"]) == 2
    groups = {image.get("group") for image in coco["images"]}
    assert None not in groups and len(groups) == 2

    # datasetvyn visar tvÃ¥ thumbnails och annotation-fliken lÃ¥st igen
    view.refresh()
    view.wait_for_refresh()
    assert len(view._thumbs) == 2
    assert not window.tabs.isTabEnabled(1)


def test_gui_capture_without_annotation_writes_nothing(qapp, app_config):
    import numpy as np

    window = MainWindow(app_config)
    frames = [StreamFrame(source_id="left", frame=synthetic_frame(fill=200),
                          detections=[], source_label="kamera")]
    window._on_capture(frames)
    service = window.dataset_service
    # avbryt (cancel) utan sparande
    window.annotation_view.cancelled.emit()
    assert service.versions() == []


def test_settings_and_theme_survive_restart(qapp, app_config, tmp_path):
    settings = QSettings(str(app_config.data_dir / "settings.ini"), QSettings.Format.IniFormat)
    settings.setValue("ui/theme", "dark")
    settings.sync()

    window = MainWindow(app_config)
    assert window.tabs.count() == 4
    assert current_theme() == "dark"
    section = ThemeSection(window.settings)
    assert section.theme_combo.currentData() == "dark"
    window.closeEvent(_close_event())


def _close_event():
    from PySide6.QtGui import QCloseEvent

    return QCloseEvent()
