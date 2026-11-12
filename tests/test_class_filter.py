"""Klassfilter per modell i detektionsvyn (TASK-53)."""

import sys
import types

import numpy as np
import pytest
from PySide6.QtCore import QSettings

from tests.conftest import FakeDetector
from xray_detector.application import model_registry
from xray_detector.domain.config import AppConfig
from xray_detector.domain.detection import Detection
from xray_detector.ui.detection_view import DetectionView
from xray_detector.ui.settings_dialog import (
    CLASS_COLUMNS,
    CLASS_LIST_MAX_HEIGHT,
    NO_CLASSES,
    ClassFilterSection,
    SettingsDialog,
)


@pytest.fixture
def model_classes() -> dict[str, list[str]]:
    """Klasserna som fake-detektorerna låtsas ha, per modellnyckel."""
    return {
        "yolo26m": ["kniv", "pistol"],
        "yolo26s": ["cigaretter", "cannabis"],
    }


@pytest.fixture
def view(qapp, tmp_path, monkeypatch, model_classes) -> DetectionView:
    def create(spec, threshold):
        detector = FakeDetector()
        detector.class_names = list(model_classes.get(spec.key, ["kniv"]))
        return detector

    monkeypatch.setattr(model_registry, "create_detector", create)
    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    view = DetectionView(
        config, QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    )
    view._detector_calls = []
    view.video_service.set_detector = view._detector_calls.append
    view._on_model_changed()
    view.wait_for_background()
    return view


def _load(view, key: str) -> None:
    """Byter modell i väljaren och väntar in laddningen."""
    view.model_combo.setCurrentIndex(view.model_combo.findData(key))
    view.wait_for_background()


def _section(view) -> ClassFilterSection:
    return view._settings_sections()[0]


def _checked(section) -> list[str]:
    return [name for name, box in section.checkboxes.items() if box.isChecked()]


# --- Sektionen ---


def test_section_lists_the_classes_with_the_disabled_ones_unchecked(qapp):
    section = ClassFilterSection(["kniv", "pistol"], {"pistol"}, lambda selected: None)

    assert list(section.checkboxes) == ["kniv", "pistol"]
    assert section.selected() == ["kniv"]


def test_section_reports_every_change(qapp):
    changes = []
    section = ClassFilterSection(["kniv", "pistol"], set(), changes.append)

    section.checkboxes["pistol"].setChecked(False)

    assert changes == [["kniv"]]


def test_section_warns_when_no_class_is_selected(qapp):
    section = ClassFilterSection(["kniv"], set(), lambda selected: None)
    assert section.warning.isHidden()

    section.checkboxes["kniv"].setChecked(False)

    assert not section.warning.isHidden()
    assert section.warning.text() == NO_CLASSES


def test_section_without_a_loaded_model_says_so(qapp):
    section = ClassFilterSection([], set(), lambda selected: None)

    assert section.checkboxes == {}
    assert section.selected() == []


# --- Markera alla / avmarkera alla (TASK-77) ---


def test_toggle_marks_every_class_when_some_are_unchecked(qapp):
    section = ClassFilterSection(["kniv", "pistol"], {"pistol"}, lambda selected: None)

    section.toggle_button.click()

    assert section.selected() == ["kniv", "pistol"]


def test_toggle_unchecks_every_class_when_all_are_checked(qapp):
    section = ClassFilterSection(["kniv", "pistol"], set(), lambda selected: None)

    section.toggle_button.click()

    assert section.selected() == []


def test_toggle_reports_one_change_for_the_whole_list(qapp):
    """Vyn ska få ett besked, inte ett per kryssruta."""
    changes = []
    section = ClassFilterSection(["kniv", "pistol"], set(), changes.append)

    section.toggle_button.click()

    assert changes == [[]]


def test_toggle_label_shows_what_the_next_click_does(qapp):
    section = ClassFilterSection(["kniv", "pistol"], set(), lambda selected: None)
    assert section.toggle_button.text() == "Av&markera alla"

    section.toggle_button.click()

    assert section.toggle_button.text() == "&Markera alla"


def test_toggle_label_follows_a_single_checkbox(qapp):
    section = ClassFilterSection(["kniv", "pistol"], set(), lambda selected: None)

    section.checkboxes["pistol"].setChecked(False)

    assert section.toggle_button.text() == "&Markera alla"


def test_toggle_updates_the_warning(qapp):
    section = ClassFilterSection(["kniv"], set(), lambda selected: None)

    section.toggle_button.click()

    assert not section.warning.isHidden()

    section.toggle_button.click()

    assert section.warning.isHidden()


# --- Många klasser (TASK-75) ---


def _grid(section):
    return section.scroll.widget().layout()


def _positions(section) -> dict[str, tuple[int, int]]:
    grid = _grid(section)
    return {
        name: grid.getItemPosition(grid.indexOf(box))[:2]
        for name, box in section.checkboxes.items()
    }


def test_section_lays_the_classes_out_in_columns(qapp):
    """Klasserna listas i flera kolumner i stället för en enda lång rad."""
    names = [f"klass-{index}" for index in range(CLASS_COLUMNS * 2 + 1)]
    section = ClassFilterSection(names, set(), lambda selected: None)

    positions = _positions(section)

    assert positions[names[0]] == (0, 0)
    assert positions[names[CLASS_COLUMNS - 1]] == (0, CLASS_COLUMNS - 1)
    assert positions[names[CLASS_COLUMNS]] == (1, 0)
    assert positions[names[-1]] == (2, 0)


def test_section_scrolls_when_the_classes_do_not_fit(qapp):
    """COCO-80 ryms inte i dialogrutan: listan rullar i stället för att växa."""
    names = [f"klass-{index}" for index in range(80)]
    section = ClassFilterSection(names, set(), lambda selected: None)
    dialog = SettingsDialog("Inställningar – Detektion", [section])
    dialog.show()
    qapp.processEvents()

    assert section.scroll.verticalScrollBar().isVisible()
    assert not section.scroll.horizontalScrollBar().isVisible()
    assert dialog.height() < CLASS_LIST_MAX_HEIGHT + 200
    dialog.close()


def test_section_with_few_classes_does_not_scroll(qapp):
    section = ClassFilterSection(["kniv", "pistol"], set(), lambda selected: None)
    dialog = SettingsDialog("Inställningar – Detektion", [section])
    dialog.show()
    qapp.processEvents()

    assert not section.scroll.verticalScrollBar().isVisible()
    dialog.close()


# --- Detektionsvyn (AC 1, 2, 4) ---


def test_settings_list_every_class_the_model_can_detect(view):
    assert list(_section(view).checkboxes) == ["kniv", "pistol"]


def test_every_class_is_selected_for_a_model_loaded_the_first_time(view):
    assert _checked(_section(view)) == ["kniv", "pistol"]
    assert view.detector.enabled_classes == {"kniv", "pistol"}


def test_class_list_follows_the_selected_model(view):
    _load(view, "yolo26s")

    assert list(_section(view).checkboxes) == ["cigaretter", "cannabis"]
    assert view.detector.enabled_classes == {"cigaretter", "cannabis"}


# --- Filtrering (AC 3) ---


class _FakeBox:
    def __init__(self, class_id):
        self.xyxy = np.array([[0.0, 0.0, 10.0, 10.0]])
        self.cls = np.array([class_id])
        self.conf = np.array([0.9])


class _FakeYolo:
    def __init__(self):
        self.names = {0: "kniv", 1: "pistol"}

    def predict(self, frame, **kwargs):
        return [types.SimpleNamespace(boxes=[_FakeBox(0), _FakeBox(1)])]


class _FakeRfDetr:
    class_names = ("kniv", "pistol")

    def predict(self, image, threshold=0.5):
        return types.SimpleNamespace(
            xyxy=np.array([[0.0, 0.0, 10.0, 10.0], [0.0, 0.0, 10.0, 10.0]]),
            class_id=np.array([0, 1]),
            confidence=np.array([0.9, 0.9]),
            data={"class_name": np.array(["kniv", "pistol"], dtype=object)},
        )


def _fake_module(monkeypatch, name: str, **attributes):
    fake = types.ModuleType(name)
    for attribute, value in attributes.items():
        setattr(fake, attribute, value)
    monkeypatch.setitem(sys.modules, name, fake)


def test_yolo_detector_drops_classes_that_are_turned_off(monkeypatch):
    _fake_module(monkeypatch, "ultralytics", YOLO=lambda weights: _FakeYolo())

    from xray_detector.infrastructure.detectors.yolo_detector import YoloDetector

    detector = YoloDetector("vikter.pt", 0.4)
    detector.set_enabled_classes(["kniv"])

    detections = detector.detect(np.zeros((10, 10, 3), np.uint8))

    assert [detection.class_name for detection in detections] == ["kniv"]


def test_rfdetr_detector_drops_classes_that_are_turned_off(monkeypatch):
    _fake_module(monkeypatch, "rfdetr", RFDETRSmall=lambda: _FakeRfDetr())

    from xray_detector.infrastructure.detectors.rfdetr_detector import RfDetrDetector

    detector = RfDetrDetector("rfdetr-small", 0.4)
    detector.set_enabled_classes(["pistol"])

    detections = detector.detect(np.zeros((10, 10, 3), np.uint8))

    assert [detection.class_name for detection in detections] == ["pistol"]


def test_detector_without_a_filter_keeps_every_class(view):
    detections = [
        Detection(0, 0, 10, 10, "kniv", 0.9),
        Detection(0, 0, 10, 10, "pistol", 0.9),
    ]

    assert view.detector.filter_detections(detections) == detections


def test_turning_a_class_off_filters_the_detector(view):
    section = _section(view)

    section.checkboxes["pistol"].setChecked(False)

    assert view.detector.enabled_classes == {"kniv"}


# --- Persistens per modell (AC 5, 6) ---


def test_the_choice_is_saved_for_the_model(view):
    section = _section(view)

    section.checkboxes["pistol"].setChecked(False)

    assert view.settings.value("detection/classes_off/yolo26m", type=str) == '["pistol"]'


def test_choices_are_kept_per_model(view):
    section = _section(view)
    section.checkboxes["pistol"].setChecked(False)

    _load(view, "yolo26s")
    _load(view, "yolo26m")

    assert _checked(_section(view)) == ["kniv"]
    assert view.detector.enabled_classes == {"kniv"}


def test_a_class_added_to_a_model_is_selected(view, model_classes):
    """Bara bortval sparas, så en ny klass i modellen är vald från början."""
    section = _section(view)
    section.checkboxes["kniv"].setChecked(False)

    model_classes["yolo26m"].append("cigaretter")
    view._on_model_changed()
    view.wait_for_background()

    assert _checked(_section(view)) == ["pistol", "cigaretter"]


# --- Alla klasser bortvalda (AC 7) ---


def test_turning_every_class_off_stops_the_detection(view):
    messages = []
    view.error_occurred.connect(messages.append)
    section = _section(view)
    view._detector_calls.clear()

    section.checkboxes["kniv"].setChecked(False)
    section.checkboxes["pistol"].setChecked(False)

    assert view.detector.enabled_classes == set()
    assert view._active_detector() is None
    assert view._detector_calls[-1] is None
    assert NO_CLASSES in messages
    assert not section.warning.isHidden()


def test_turning_a_class_back_on_restarts_the_detection(view):
    section = _section(view)
    section.checkboxes["kniv"].setChecked(False)
    section.checkboxes["pistol"].setChecked(False)
    view._detector_calls.clear()

    section.checkboxes["kniv"].setChecked(True)

    assert view._detector_calls == [view.detector]
    assert view._active_detector() is view.detector


# --- Markera alla / avmarkera alla i vyn (TASK-77) ---


def test_toggle_in_the_view_saves_the_choice_and_stops_the_detection(view):
    section = _section(view)
    view._detector_calls.clear()

    section.toggle_button.click()

    assert view.settings.value("detection/classes_off/yolo26m", type=str) == '["kniv", "pistol"]'
    assert view.detector.enabled_classes == set()
    assert view._detector_calls == [None]


def test_toggle_back_on_restarts_the_detection_once(view):
    section = _section(view)
    section.toggle_button.click()
    view._detector_calls.clear()

    section.toggle_button.click()

    assert view.detector.enabled_classes == {"kniv", "pistol"}
    assert view._detector_calls == [view.detector]
