"""Upptagenindikator och arbete utanför GUI-tråden i vyerna (TASK-40)."""

import threading
import time

import numpy as np
import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QDialog

from tests.conftest import FakeDetector, synthetic_frame
from xray_detector.application import model_registry
from xray_detector.domain.capture import StreamFrame
from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.infrastructure.dataset_store.store import DatasetStore
from xray_detector.ui.annotation_view import AnnotationView, RectItem
from xray_detector.ui.busy_indicator import BusyIndicator
from xray_detector.ui.dataset_view import DatasetView
from xray_detector.ui.detection_view import DetectionView
from xray_detector.ui.main_window import MainWindow
from xray_detector.ui.variation_dialog import VariationDialog

# testerna startar MainWindow och tar därför sekunder (TASK-154)
pytestmark = pytest.mark.slow


def _spin_until(qapp, predicate, timeout_s: float = 5.0) -> bool:
    """Kör händelseloopen tills villkoret är uppfyllt eller tiden tar slut."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return True
        qapp.processEvents()
        time.sleep(0.005)
    return predicate()




@pytest.fixture
def dataset_store(tmp_path) -> DatasetStore:
    service = DatasetStore(tmp_path / "datasets")
    service.add_samples([
        AnnotatedImage(np.full((30, 40, 3), 60, np.uint8),
                       [{"class_name": "kniv", "bbox": [2, 2, 8, 8]}]),
        AnnotatedImage(np.full((30, 40, 3), 120, np.uint8),
                       [{"class_name": "kniv", "bbox": [4, 4, 8, 8]}]),
    ])
    return service


@pytest.fixture
def detection_view(qapp, config, settings) -> DetectionView:
    view = DetectionView(config, settings)
    yield view
    view.wait_for_background()


def _blocking_detector(monkeypatch, release: threading.Event, threads: list) -> None:
    """Modelladdning som står kvar tills testet släpper den."""

    def create(spec, threshold):
        threads.append(threading.get_ident())
        release.wait(5)
        return FakeDetector()

    monkeypatch.setattr(model_registry, "create_detector", create)


# --- Detektionsvyn: modelladdning (AC 1-5) ---


def test_model_load_shows_animated_indicator(qapp, detection_view, monkeypatch):
    release = threading.Event()
    threads: list = []
    _blocking_detector(monkeypatch, release, threads)
    try:
        detection_view._on_model_changed()

        assert detection_view.busy.is_busy(), "indikatorn ska visas innan arbetet börjar"
        assert _spin_until(qapp, detection_view.busy.is_revealed)
        angle = detection_view.busy.angle()
        assert _spin_until(qapp, lambda: detection_view.busy.angle() != angle), (
            "snurran ska animeras medan modellen laddas"
        )
    finally:
        release.set()

    detection_view.wait_for_background()

    assert not detection_view.busy.is_busy()
    assert detection_view.detector is not None


def test_model_load_runs_off_the_gui_thread(qapp, detection_view, monkeypatch):
    release = threading.Event()
    threads: list = []
    _blocking_detector(monkeypatch, release, threads)
    try:
        detection_view._on_model_changed()
        assert _spin_until(qapp, lambda: threads)
        assert threads[0] != threading.get_ident()

        # GUI-tråden är ledig: en noll-timer hinner köra medan laddningen pågår
        fired: list = []
        QTimer.singleShot(0, lambda: fired.append(True))
        assert _spin_until(qapp, lambda: fired)
        assert detection_view._model_task is not None, "laddningen pågår fortfarande"
    finally:
        release.set()

    detection_view.wait_for_background()


def test_model_combo_is_disabled_while_loading(qapp, detection_view, monkeypatch):
    release = threading.Event()
    threads: list = []
    _blocking_detector(monkeypatch, release, threads)
    try:
        detection_view._on_model_changed()

        assert not detection_view.model_combo.isEnabled()
        assert _spin_until(qapp, lambda: threads)
        # ett andra val under laddningen får inte starta en ny laddning
        detection_view._on_model_changed()
        assert len(threads) == 1
    finally:
        release.set()

    detection_view.wait_for_background()

    assert detection_view.model_combo.isEnabled()


def test_failed_load_reports_the_same_message_and_detaches(
    qapp, detection_view, monkeypatch
):
    messages: list = []
    detection_view.error_occurred.connect(messages.append)
    detached: list = []
    detection_view.camera_service.set_detector = detached.append

    def broken(spec, threshold):
        raise RuntimeError("trasig modell")

    monkeypatch.setattr(model_registry, "create_detector", broken)

    detection_view._on_model_changed()
    detection_view.wait_for_background()

    assert detection_view.detector is None
    assert detached == [None]
    assert "Kunde inte ladda modell: trasig modell" in messages
    assert not detection_view.busy.is_busy()
    assert detection_view.model_combo.isEnabled()


# --- Detektionsvyn: enhetskontrollen vid start (AC 11) ---


def test_device_check_runs_off_the_gui_thread(qapp, detection_view, monkeypatch):
    release = threading.Event()
    threads: list = []

    def slow_status():
        threads.append(threading.get_ident())
        release.wait(5)
        return "Enhet: CUDA (testkort)"

    monkeypatch.setattr(model_registry, "device_status", slow_status)
    try:
        detection_view.check_device()

        assert detection_view.device_label.text() == "Enhet: kontrollerar..."
        assert _spin_until(qapp, lambda: threads)
        assert threads[0] != threading.get_ident()
    finally:
        release.set()

    detection_view.wait_for_background()

    assert detection_view.device_label.text() == "Enhet: CUDA (testkort)"


def test_main_window_opens_before_the_device_check_finishes(qapp, config, monkeypatch):
    release = threading.Event()
    threads: list = []

    def slow_status():
        threads.append(threading.get_ident())
        release.wait(5)
        return "Enhet: CUDA (testkort)"

    monkeypatch.setattr(model_registry, "device_status", slow_status)
    try:
        window = MainWindow(config)

        assert window.detection_view.device_label.text() == "Enhet: kontrollerar..."
        assert _spin_until(qapp, lambda: threads)
        assert threads[0] != threading.get_ident()
    finally:
        release.set()

    window.detection_view.wait_for_background()
    window.dataset_view.wait_for_refresh()

    assert window.detection_view.device_label.text() == "Enhet: CUDA (testkort)"


# --- Datasetvyn: omladdning av bildlistan (AC 8) ---


def test_dataset_refresh_shows_indicator_and_builds_list(
    qapp, config, dataset_store, settings
):
    view = DatasetView(config, dataset_store, settings)
    view.refresh()

    assert view.busy.is_busy()
    view.wait_for_refresh()

    assert not view.busy.is_busy()
    assert len(view._thumbs) == 2


def test_dataset_refresh_decodes_off_the_gui_thread(
    qapp, config, dataset_store, settings, monkeypatch
):
    threads: list = []
    original = DatasetView._load

    def recording(self):
        threads.append(threading.get_ident())
        return original(self)

    monkeypatch.setattr(DatasetView, "_load", recording)
    view = DatasetView(config, dataset_store, settings)
    view.wait_for_refresh()

    assert threads
    assert all(ident != threading.get_ident() for ident in threads)


# --- Datasetvyn: export (AC 9) ---


def test_export_shows_indicator_and_reports_result(qapp, config, settings, dataset_store):
    view = DatasetView(config, dataset_store, settings)
    view.wait_for_refresh()
    messages: list = []
    view.status_changed.connect(messages.append)

    view._on_export_coco()

    assert view.busy.is_busy()
    assert not view.export_coco_button.isEnabled()
    view.wait_for_export()

    assert not view.busy.is_busy()
    assert view.export_coco_button.isEnabled()
    assert messages and messages[0].startswith("Exporterade COCO till ")


def test_export_yolo_shows_indicator_and_reports_result(
    qapp, config, settings, dataset_store
):
    view = DatasetView(config, dataset_store, settings)
    view.wait_for_refresh()
    messages: list = []
    view.status_changed.connect(messages.append)

    view._on_export_yolo()
    view.wait_for_export()

    assert messages and messages[0].startswith("Exporterade YOLO till ")


def test_export_failure_is_reported(qapp, config, settings, dataset_store, monkeypatch):
    view = DatasetView(config, dataset_store, settings)
    view.wait_for_refresh()
    messages: list = []
    view.status_changed.connect(messages.append)

    def broken(store, export_root, ratio):
        raise OSError("disken är full")

    monkeypatch.setattr("xray_detector.ui.dataset_view.export_yolo", broken)
    view._on_export_yolo()
    view.wait_for_export()

    assert messages == ["Export av YOLO misslyckades: disken är full"]
    assert view.export_yolo_button.isEnabled()
    assert not view.busy.is_busy()


def test_export_keeps_the_indicator_while_the_list_reloads(
    qapp, config, settings, dataset_store, monkeypatch
):
    """Export och omladdning delar indikatorn: den släcks först när båda är klara."""
    release = threading.Event()

    def slow_export(store, export_root):
        release.wait(5)
        return export_root / "coco"

    monkeypatch.setattr("xray_detector.ui.dataset_view.export_coco", slow_export)
    view = DatasetView(config, dataset_store, settings)
    view.wait_for_refresh()

    view._on_export_coco()
    view.refresh()
    view.wait_for_refresh()

    assert view.busy.is_busy()
    release.set()
    view.wait_for_export()

    assert not view.busy.is_busy()


# --- Datasetvyn: utökning med bildvariationer (TASK-88) ---


def _accept_with_rotation(dialog):
    """Väljer en rotation i dialogen och genomför den."""
    dialog.rotation.setChecked(True)
    return QDialog.DialogCode.Accepted


def test_variations_show_indicator_and_report_result(
    qapp, config, settings, dataset_store, monkeypatch
):
    monkeypatch.setattr(VariationDialog, "exec", _accept_with_rotation)
    view = DatasetView(config, dataset_store, settings)
    view.wait_for_refresh()
    messages: list = []
    view.status_changed.connect(messages.append)

    view._on_add_variations()

    assert view.busy.is_busy()
    assert not view.variation_button.isEnabled()
    view.wait_for_variations()
    view.wait_for_refresh()

    assert not view.busy.is_busy()
    assert view.variation_button.isEnabled()
    assert messages and messages[0].startswith("Lade till ")


def test_variation_failure_is_reported(
    qapp, config, settings, dataset_store, monkeypatch
):
    def broken(settings, seed=None):
        raise OSError("disken är full")

    monkeypatch.setattr(VariationDialog, "exec", _accept_with_rotation)
    monkeypatch.setattr(dataset_store, "add_variations", broken)
    view = DatasetView(config, dataset_store, settings)
    view.wait_for_refresh()
    messages: list = []
    view.status_changed.connect(messages.append)

    view._on_add_variations()
    view.wait_for_variations()

    assert messages == ["Kunde inte skapa bildvariationer: disken är full"]
    assert view.variation_button.isEnabled()
    assert not view.busy.is_busy()


# --- Annoteringsvyn: sparning (AC 10) ---


def _dirty_annotation_view(config, dataset_store, settings) -> AnnotationView:
    view = AnnotationView(config, dataset_store, settings)
    view.load_captures([StreamFrame("left", synthetic_frame(), [], "kamera")])
    view.canvases[0].rects.append(RectItem(5, 5, 30, 30, "kniv"))
    view.canvases[0]._mark_dirty()
    return view


def test_save_shows_indicator_and_writes_dataset(qapp, config, settings, dataset_store):
    view = _dirty_annotation_view(config, dataset_store, settings)

    view.save()

    assert view.busy.is_busy()
    assert not view.save_button.isEnabled()
    view.wait_for_save()

    assert not view.busy.is_busy()
    assert view.save_button.isEnabled()
    assert not view.is_dirty()
    assert dataset_store.metadata()["num_images"] == 3


def test_save_runs_off_the_gui_thread(qapp, config, settings, dataset_store, monkeypatch):
    threads: list = []
    original = dataset_store.add_samples

    def recording(*args, **kwargs):
        threads.append(threading.get_ident())
        return original(*args, **kwargs)

    monkeypatch.setattr(dataset_store, "add_samples", recording)
    view = _dirty_annotation_view(config, dataset_store, settings)

    view.save()
    view.wait_for_save()

    assert threads and threads[0] != threading.get_ident()


# --- Komponenten delas av alla vyer (AC 6) ---


def test_views_share_the_busy_indicator_component(
    qapp, config, settings, dataset_store
):
    detection = DetectionView(config, settings)
    annotation = AnnotationView(config, dataset_store, settings)
    dataset = DatasetView(config, dataset_store, settings)
    try:
        for view in (detection, annotation, dataset):
            assert isinstance(view.busy, BusyIndicator)
            assert view.busy.parentWidget() is view
    finally:
        dataset.wait_for_refresh()
        detection.wait_for_background()
