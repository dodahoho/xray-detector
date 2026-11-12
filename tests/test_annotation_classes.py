"""Annoteringsvyns klasslista: modellens klasser är standard, datasetet är master (TASK-61)."""

import numpy as np
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox

from tests.conftest import FakeDetector, synthetic_frame
from xray_detector.application.dataset_service import DatasetService
from xray_detector.domain.capture import StreamFrame
from xray_detector.domain.config import AppConfig
from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.ui.annotation_view import AnnotationView


def make_view(tmp_path, model_classes=None, settings=None) -> tuple[AnnotationView, DatasetService]:
    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    service = DatasetService(config.dataset_dir)
    settings = settings or QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    view = AnnotationView(config, service, settings, model_classes=model_classes)
    return view, service


def model(*names: str):
    return lambda: list(names)


def capture() -> StreamFrame:
    return StreamFrame("left", synthetic_frame(), [], "kamera")


def sample(class_name: str) -> AnnotatedImage:
    return AnnotatedImage(
        np.full((40, 50, 3), 100, dtype=np.uint8),
        [{"class_name": class_name, "bbox": [2, 3, 10, 12]}],
    )


# --- Standardvärden från modellen (AC 1) ---


def test_annotation_view_lists_the_models_classes(qapp, tmp_path):
    view, _ = make_view(tmp_path, model("kniv", "pistol"))

    assert view._class_names() == ["kniv", "pistol"]


def test_model_classes_are_written_to_the_dataset_when_the_view_opens(qapp, tmp_path):
    view, service = make_view(tmp_path, model("kniv", "pistol"))

    view.load_captures([capture()])

    assert service.classes() == ["kniv", "pistol"]


def test_model_classes_are_not_written_before_the_view_opens(qapp, tmp_path):
    _, service = make_view(tmp_path, model("kniv", "pistol"))

    assert service.classes() == [], "först när vyn öppnas blir modellens klasser datasetets"


def test_config_classes_are_the_fallback_without_a_model(qapp, tmp_path):
    view, _ = make_view(tmp_path)

    assert view._class_names() == AppConfig().classes


# --- Datasetet är master (AC 2) ---


def test_dataset_classes_win_over_the_model(qapp, tmp_path):
    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    service = DatasetService(config.dataset_dir)
    service.set_classes(["cigaretter"])

    view = AnnotationView(
        config,
        service,
        QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat),
        model_classes=model("kniv"),
    )

    assert view._class_names() == ["cigaretter"]


def test_class_list_survives_a_new_view_with_another_model(qapp, tmp_path):
    first, service = make_view(tmp_path, model("kniv"))
    first.load_captures([capture()])

    second = AnnotationView(
        first.config,
        service,
        QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat),
        model_classes=model("pistol"),
    )

    assert second._class_names() == ["kniv"]


def test_classes_are_not_stored_in_the_settings(qapp, tmp_path):
    view, _ = make_view(tmp_path, model("kniv"))

    view.save_settings()

    assert view.settings.value("annotation/classes") is None


# --- Lägga till och ta bort klasser (AC 3) ---


def test_added_class_is_stored_in_the_dataset(qapp, tmp_path):
    view, service = make_view(tmp_path, model("kniv"))
    view.load_captures([capture()])

    view.class_combo.setEditText("cigaretter")
    view._on_add_class()

    assert view._class_names() == ["kniv", "cigaretter"]
    assert service.classes() == ["kniv", "cigaretter"]


def test_removed_class_is_removed_from_the_dataset(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr(
        QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
    )
    view, service = make_view(tmp_path, model("kniv", "pistol"))
    view.load_captures([capture()])
    view.class_combo.setCurrentIndex(view.class_combo.findText("pistol"))

    view._on_remove_class()

    assert view._class_names() == ["kniv"]
    assert service.classes() == ["kniv"]


def test_class_in_use_cannot_be_removed(qapp, tmp_path, monkeypatch):
    messages: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "information", staticmethod(lambda *a, **k: messages.append(a[2]))
    )
    view, service = make_view(tmp_path, model("kniv"))
    service.add_samples([sample("kniv")])
    view.refresh_classes()

    view._on_remove_class()

    assert messages and "används av sparade annoteringar" in messages[0]
    assert service.classes() == ["kniv"]


def test_removing_every_class_keeps_the_list_empty(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr(
        QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
    )
    view, service = make_view(tmp_path, model("kniv"))
    view.load_captures([capture()])

    view._on_remove_class()
    view.refresh_classes(seed_dataset=True)

    assert service.classes() == []
    assert view._class_names() == [], "modellens klasser fyller inte på ett tomt dataset igen"


# --- Kategorierna i datasetet (AC 4) ---


def test_set_classes_keeps_the_category_ids(tmp_path):
    service = DatasetService(tmp_path / "datasets")
    service.set_classes(["kniv", "pistol"])

    service.set_classes(["pistol", "cigaretter"])

    categories = service.load_coco()["categories"]
    assert [(c["id"], c["name"]) for c in categories] == [(1, "pistol"), (2, "cigaretter")]


def test_new_category_gets_a_free_id_after_a_removal(tmp_path):
    service = DatasetService(tmp_path / "datasets")
    service.set_classes(["kniv", "pistol"])
    service.set_classes(["pistol"])

    service.add_samples([sample("cigaretter")])

    categories = service.load_coco()["categories"]
    assert [(c["id"], c["name"]) for c in categories] == [(1, "pistol"), (2, "cigaretter")]


# --- Kopplingen från detektionsvyn (AC 1) ---


def test_main_window_seeds_the_annotation_view_from_the_model(qapp, tmp_path, monkeypatch):
    from xray_detector.application import model_registry
    from xray_detector.ui.main_window import MainWindow

    monkeypatch.setattr(
        model_registry, "create_detector", lambda spec, threshold: FakeDetector("kniv")
    )
    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    window = MainWindow(config)
    window.detection_view._on_model_changed()
    window.detection_view.wait_for_background()

    window.annotation_view.load_captures([capture()])

    assert window.annotation_view._class_names() == ["kniv"]
    assert window.dataset_service.classes() == ["kniv"]
