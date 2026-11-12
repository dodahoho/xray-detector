"""Annoteringsvyns klasslista: datasetet är master och modellen erbjuds i en fråga (TASK-61, TASK-71)."""

import numpy as np
from PySide6.QtCore import QEvent, QPointF, QSettings, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QInputDialog, QMessageBox

from tests.conftest import FakeDetector, synthetic_frame
from xray_detector.application.dataset_service import DatasetService
from xray_detector.domain.capture import StreamFrame
from xray_detector.domain.config import AppConfig
from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.domain.detection import Detection
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


def capture(*class_names: str, y: int = 2) -> StreamFrame:
    detections = [Detection(2, y, 20, y + 18, name, 0.9) for name in class_names]
    return StreamFrame("left", synthetic_frame(), detections, "kamera")


def sample(class_name: str) -> AnnotatedImage:
    return AnnotatedImage(
        np.full((40, 50, 3), 100, dtype=np.uint8),
        [{"class_name": class_name, "bbox": [2, 3, 10, 12]}],
    )


def answer(monkeypatch, button, messages: list[str] | None = None) -> None:
    """Svarar på QMessageBox.question och samlar dialogtexterna."""

    def question(parent, title, text, *args, **kwargs):
        if messages is not None:
            messages.append(text)
        return button

    monkeypatch.setattr(QMessageBox, "question", staticmethod(question))


def click(canvas, point) -> None:
    def event(event_type):
        return QMouseEvent(
            event_type,
            QPointF(point),
            QPointF(point),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )

    canvas.mousePressEvent(event(QEvent.Type.MouseButtonPress))
    canvas.mouseReleaseEvent(event(QEvent.Type.MouseButtonRelease))


def sized_canvas(view: AnnotationView):
    """Första canvasen med en känd storlek, så etiketten går att träffa."""
    canvas = view.canvases[0]
    canvas.resize(160, 120)
    return canvas


# --- Tom lista vid nyinstallation (AC 1) ---


def test_annotation_list_is_empty_by_default(qapp, tmp_path):
    view, service = make_view(tmp_path, model("kniv", "pistol"))

    assert view._class_names() == []
    assert service.classes() == []


def test_config_classes_do_not_fill_the_annotation_list(qapp, tmp_path):
    view, _ = make_view(tmp_path)

    assert AppConfig().classes, "config.classes finns kvar för overlayfärgerna"
    assert view._class_names() == []


# --- Frågan om modellens klasser (AC 2) ---


def test_model_classes_are_offered_when_the_list_is_empty(qapp, tmp_path, monkeypatch):
    messages: list[str] = []
    answer(monkeypatch, QMessageBox.StandardButton.Yes, messages)
    view, service = make_view(tmp_path, model("kniv", "pistol"))

    view.load_captures([capture()])

    assert view._class_names() == ["kniv", "pistol"]
    assert service.classes() == ["kniv", "pistol"]
    assert messages and "2 klasser" in messages[0]
    assert "kniv" not in messages[0] and "pistol" not in messages[0]


def test_the_offer_counts_a_single_class_in_the_singular(qapp, tmp_path, monkeypatch):
    messages: list[str] = []
    answer(monkeypatch, QMessageBox.StandardButton.Yes, messages)
    view, _ = make_view(tmp_path, model("kniv"))

    view.load_captures([capture()])

    assert messages and "1 klass " in messages[0]


def test_declining_the_offer_keeps_the_list_empty(qapp, tmp_path, monkeypatch):
    answer(monkeypatch, QMessageBox.StandardButton.No)
    view, service = make_view(tmp_path, model("kniv", "pistol"))

    view.load_captures([capture()])

    assert view._class_names() == []
    assert service.classes() == []


def test_no_offer_without_a_model(qapp, tmp_path, monkeypatch):
    messages: list[str] = []
    answer(monkeypatch, QMessageBox.StandardButton.Yes, messages)
    view, _ = make_view(tmp_path)

    view.load_captures([capture()])

    assert messages == []
    assert view._class_names() == []


def test_no_offer_when_the_dataset_already_has_classes(qapp, tmp_path, monkeypatch):
    messages: list[str] = []
    answer(monkeypatch, QMessageBox.StandardButton.Yes, messages)
    view, service = make_view(tmp_path, model("kniv", "pistol"))
    service.set_classes(["cigaretter"])

    view.load_captures([capture()])

    assert messages == []
    assert view._class_names() == ["cigaretter"]


def test_the_offer_returns_when_the_list_is_empty_again(qapp, tmp_path, monkeypatch):
    answer(monkeypatch, QMessageBox.StandardButton.Yes)
    view, service = make_view(tmp_path, model("kniv"))
    view.load_captures([capture()])
    view._on_remove_class()

    view.load_captures([capture()])

    assert service.classes() == ["kniv"]


# --- Klasser som bildparet detekterat men listan saknar (AC 3) ---


def test_detected_class_missing_from_the_list_is_offered_by_name(qapp, tmp_path, monkeypatch):
    messages: list[str] = []
    answer(monkeypatch, QMessageBox.StandardButton.Yes, messages)
    view, service = make_view(tmp_path, model("kniv"))
    service.set_classes(["kniv"])

    view.load_captures([capture("pistol")])

    assert view._class_names() == ["kniv", "pistol"]
    assert service.classes() == ["kniv", "pistol"]
    assert any('"pistol"' in message for message in messages)


def test_declining_the_missing_class_keeps_the_list(qapp, tmp_path, monkeypatch):
    answer(monkeypatch, QMessageBox.StandardButton.No)
    view, service = make_view(tmp_path, model("kniv"))
    service.set_classes(["kniv"])

    view.load_captures([capture("pistol")])

    assert view._class_names() == ["kniv"]
    assert service.classes() == ["kniv"]


def test_known_detected_class_is_not_offered(qapp, tmp_path, monkeypatch):
    messages: list[str] = []
    answer(monkeypatch, QMessageBox.StandardButton.Yes, messages)
    view, service = make_view(tmp_path, model("kniv"))
    service.set_classes(["kniv"])

    view.load_captures([capture("kniv")])

    assert messages == []
    assert view._class_names() == ["kniv"]


def test_each_missing_class_is_offered_once(qapp, tmp_path, monkeypatch):
    messages: list[str] = []
    answer(monkeypatch, QMessageBox.StandardButton.Yes, messages)
    view, service = make_view(tmp_path, model("kniv"))
    service.set_classes(["kniv"])

    view.load_captures([capture("pistol", "pistol", "cigaretter")])

    assert view._class_names() == ["kniv", "pistol", "cigaretter"]
    assert len(messages) == 2


# --- Datasetet är master (AC 4) ---


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


def test_class_list_survives_a_new_view_with_another_model(qapp, tmp_path, monkeypatch):
    answer(monkeypatch, QMessageBox.StandardButton.Yes)
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


def test_added_class_is_stored_in_the_dataset(qapp, tmp_path, monkeypatch):
    answer(monkeypatch, QMessageBox.StandardButton.Yes)
    view, service = make_view(tmp_path, model("kniv"))
    view.load_captures([capture()])

    view.class_combo.setEditText("cigaretter")
    view._on_add_class()

    assert view._class_names() == ["kniv", "cigaretter"]
    assert service.classes() == ["kniv", "cigaretter"]


def test_removed_class_is_removed_from_the_dataset(qapp, tmp_path, monkeypatch):
    answer(monkeypatch, QMessageBox.StandardButton.Yes)
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
    answer(monkeypatch, QMessageBox.StandardButton.Yes)
    view, service = make_view(tmp_path, model("kniv"))
    view.load_captures([capture()])

    view._on_remove_class()
    view.refresh_classes()

    assert service.classes() == []
    assert view._class_names() == []


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


# --- Klick på klassnamnet i bilden (AC 5) ---


def test_clicking_the_class_label_offers_the_dataset_classes(qapp, tmp_path, monkeypatch):
    answer(monkeypatch, QMessageBox.StandardButton.Yes)
    view, _ = make_view(tmp_path, model("kniv", "pistol"))
    view.load_captures([capture("kniv", y=20)])
    canvas = sized_canvas(view)
    item = canvas.rects[0]
    offered: list[list[str]] = []

    def get_item(parent, title, label, items, current=0, editable=True, *args, **kwargs):
        offered.append(list(items))
        return "pistol", True

    monkeypatch.setattr(QInputDialog, "getItem", staticmethod(get_item))

    click(canvas, canvas._label_rect(item).center())

    assert offered == [["kniv", "pistol"]]
    assert item.class_name == "pistol"
    assert canvas.dirty
    assert view.class_combo.currentText() == "pistol"


def test_clicking_the_class_label_selects_the_annotation(qapp, tmp_path, monkeypatch):
    answer(monkeypatch, QMessageBox.StandardButton.Yes)
    view, _ = make_view(tmp_path, model("kniv", "pistol"))
    view.load_captures([capture("kniv", y=20)])
    canvas = sized_canvas(view)
    item = canvas.rects[0]
    monkeypatch.setattr(
        QInputDialog, "getItem", staticmethod(lambda *a, **k: ("pistol", True))
    )

    click(canvas, canvas._label_rect(item).center())

    assert canvas.selected is item


def test_cancelling_the_class_dialog_keeps_the_class(qapp, tmp_path, monkeypatch):
    answer(monkeypatch, QMessageBox.StandardButton.Yes)
    view, _ = make_view(tmp_path, model("kniv", "pistol"))
    view.load_captures([capture("kniv", y=20)])
    canvas = sized_canvas(view)
    item = canvas.rects[0]
    monkeypatch.setattr(
        QInputDialog, "getItem", staticmethod(lambda *a, **k: ("pistol", False))
    )

    click(canvas, canvas._label_rect(item).center())

    assert item.class_name == "kniv"
    assert not canvas.dirty


def test_clicking_the_annotation_body_does_not_open_the_class_dialog(
    qapp, tmp_path, monkeypatch
):
    answer(monkeypatch, QMessageBox.StandardButton.Yes)
    view, _ = make_view(tmp_path, model("kniv", "pistol"))
    view.load_captures([capture("kniv", y=20)])
    canvas = sized_canvas(view)
    item = canvas.rects[0]
    called: list[tuple] = []
    monkeypatch.setattr(
        QInputDialog,
        "getItem",
        staticmethod(lambda *a, **k: called.append(a) or ("pistol", True)),
    )

    click(canvas, canvas._handle_points(item.rect)["_center"])

    assert called == []
    assert item.class_name == "kniv"


# --- Kopplingen från detektionsvyn (AC 2) ---


def test_main_window_offers_the_models_classes(qapp, tmp_path, monkeypatch):
    from xray_detector.application import model_registry
    from xray_detector.ui.main_window import MainWindow

    answer(monkeypatch, QMessageBox.StandardButton.Yes)
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


def window_with_model(tmp_path, monkeypatch):
    """Ett huvudfönster med en laddad modell som har klassen kniv."""
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
    return window


def record_tab(monkeypatch, window, seen: list[tuple[int, bool]]) -> None:
    """Svarar ja på frågorna och noterar vilken flik som var öppen då."""

    def question(parent, title, text, *args, **kwargs):
        seen.append((window.tabs.currentIndex(), window.tabs.isTabEnabled(1)))
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(QMessageBox, "question", staticmethod(question))


def test_the_class_dialog_opens_after_the_switch_to_the_annotation_view(
    qapp, tmp_path, monkeypatch
):
    """Frågan ska komma i annoteringsvyn, inte i detektionsvyn före växlingen."""
    seen: list[tuple[int, bool]] = []
    window = window_with_model(tmp_path, monkeypatch)
    record_tab(monkeypatch, window, seen)

    window._on_capture([capture()])

    assert seen == [(1, True)]
    assert window.annotation_view._class_names() == ["kniv"]


def test_the_class_dialog_opens_after_the_switch_from_the_dataset_view(
    qapp, tmp_path, monkeypatch
):
    seen: list[tuple[int, bool]] = []
    window = window_with_model(tmp_path, monkeypatch)
    window.dataset_service.add_samples(
        [AnnotatedImage(np.full((40, 50, 3), 100, dtype=np.uint8), [])]
    )
    window.dataset_view.refresh()
    window.dataset_view.wait_for_refresh()
    record_tab(monkeypatch, window, seen)

    window.dataset_view._on_thumb_double_clicked(window.dataset_view._thumbs[0])

    assert seen == [(1, True)]
    assert window.annotation_view._class_names() == ["kniv"]
