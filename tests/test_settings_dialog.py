"""Globala inställningar i fliken och egna inställningar per vy (TASK-43)."""

import numpy as np
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QDialog, QDialogButtonBox

from xray_detector.application.dataset_service import DatasetService
from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.ui.main_window import MainWindow
from xray_detector.ui.settings_dialog import (
    SORT_KEY,
    SORT_NEWEST,
    SORT_OLDEST,
    TRAIN_RATIO_KEY,
    ClassFilterSection,
    DatasetSortSection,
    SettingsDialog,
    ThemeSection,
    TrainingScheduleSection,
    TrainValSplitSection,
    settings_button,
    train_ratio,
)
from xray_detector.ui.theme import apply_theme, current_theme
from xray_detector.ui.training_view import TrainingView

VIEWS = ("detection_view", "annotation_view", "dataset_view", "training_view")


@pytest.fixture(autouse=True)
def reset_theme(qapp):
    """Temat är globalt: lämna tillbaka det till system efter varje test."""
    yield
    apply_theme(qapp, "system")


@pytest.fixture
def settings(tmp_path) -> QSettings:
    return QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)


@pytest.fixture
def window(qapp, config):
    window = MainWindow(config)
    yield window
    window.detection_view.wait_for_background()
    window.dataset_view.wait_for_refresh()
    window.close()


def _top_row(view):
    """Vyns översta rad, där inställningsknappen ska ligga sist."""
    return view.layout().itemAt(0).layout()


def _opened_dialog(monkeypatch, button) -> SettingsDialog:
    """Klickar på knappen och fångar dialogen i stället för att öppna den modalt."""
    opened: list = []
    monkeypatch.setattr(SettingsDialog, "exec", lambda self: opened.append(self))
    button.click()
    assert len(opened) == 1
    return opened[0]


def test_settings_tab_holds_the_global_theme(window):
    assert window.tabs.count() == 5
    assert window.tabs.tabText(4) == "Instä&llningar"
    assert window.tabs.widget(4) is window.settings_view
    assert isinstance(window.settings_view.theme_section, ThemeSection)


def test_tab_row_has_five_tabs(window):
    assert [window.tabs.tabText(index) for index in range(5)] == [
        "&Detektion",
        "&Annotation",
        "Data&set",
        "&Träning",
        "Instä&llningar",
    ]


def test_every_view_has_a_settings_button_with_a_gear(window):
    for name in VIEWS:
        button = getattr(window, name).settings_button
        assert button.text() == "&Inställningar"
        assert not button.icon().isNull(), "kugghjulet ska stå framför texten"
        assert button.shortcut().toString() == "Alt+I"


def test_settings_button_sits_top_right_in_every_view(window):
    for name in VIEWS:
        view = getattr(window, name)
        row = _top_row(view)
        assert row.itemAt(row.count() - 1).widget() is view.settings_button, name


def test_view_without_own_settings_keeps_a_disabled_button(window):
    button = window.annotation_view.settings_button
    assert not button.isEnabled()
    assert button.toolTip() == "Vyn har inga egna inställningar"

    for name in ("detection_view", "training_view", "dataset_view"):
        assert getattr(window, name).settings_button.isEnabled(), name


def test_dataset_settings_open_the_sort_order(qapp, window, monkeypatch):
    dialog = _opened_dialog(monkeypatch, window.dataset_view.settings_button)

    assert dialog.windowTitle() == "Inställningar – Dataset"
    assert dialog.findChild(DatasetSortSection) is not None
    assert dialog.findChild(ThemeSection) is None, "temat hör till inställningsfliken"


def test_dataset_sort_order_is_read_and_written(qapp, settings):
    section = DatasetSortSection(settings)
    assert section.order_combo.currentData() == SORT_NEWEST

    section.order_combo.setCurrentIndex(section.order_combo.findData(SORT_OLDEST))

    assert settings.value(SORT_KEY) == SORT_OLDEST
    assert DatasetSortSection(settings).order_combo.currentData() == SORT_OLDEST


def test_detection_settings_open_the_class_filter(qapp, window, monkeypatch):
    dialog = _opened_dialog(monkeypatch, window.detection_view.settings_button)

    assert dialog.windowTitle() == "Inställningar – Detektion"
    assert dialog.findChild(ClassFilterSection) is not None
    assert dialog.findChild(ThemeSection) is None, "temat hör till inställningsfliken"


def test_training_settings_open_the_schedule(qapp, window, monkeypatch):
    dialog = _opened_dialog(monkeypatch, window.training_view.settings_button)

    assert dialog.windowTitle() == "Inställningar – Träning"
    assert dialog.findChild(TrainingScheduleSection) is not None
    assert dialog.findChild(ThemeSection) is None, "temat hör till inställningsfliken"


def test_training_settings_open_the_train_val_split(qapp, window, monkeypatch):
    """Andelen train/val ställs in i träningsvyns inställningar (TASK-72)."""
    dialog = _opened_dialog(monkeypatch, window.training_view.settings_button)

    assert dialog.findChild(TrainValSplitSection) is not None


def test_train_ratio_is_read_and_written(qapp, settings):
    assert train_ratio(settings) == 0.8
    section = TrainValSplitSection(settings)
    assert section.ratio.value() == 80

    section.ratio.setValue(50)

    assert settings.value(TRAIN_RATIO_KEY, type=int) == 50
    assert train_ratio(settings) == 0.5
    assert TrainValSplitSection(settings).ratio.value() == 50


def test_train_ratio_keeps_a_group_on_each_side(qapp, settings):
    """Både train och val får minst en grupp, även om värdet ligger utanför 1-99."""
    settings.setValue(TRAIN_RATIO_KEY, 0)
    assert train_ratio(settings) == 0.01

    settings.setValue(TRAIN_RATIO_KEY, 100)
    assert train_ratio(settings) == 0.99


def test_training_view_shows_train_val_in_pairs(qapp, config, settings):
    """Redovisningen räknar bildpar och följer den valda andelen (TASK-72)."""
    service = DatasetService(config.dataset_dir)
    service.set_classes(["kniv"])
    for group in range(6):
        service.add_samples([
            AnnotatedImage(
                np.full((30, 40, 3), 40 + group * 20, np.uint8),
                [{"class_name": "kniv", "bbox": [2, 2, 8, 8]}],
            )
            for _ in range(2)
        ])
    view = TrainingView(config, service, settings)

    assert "Train/val: 5/1 par" in view.dataset_info.text()

    settings.setValue(TRAIN_RATIO_KEY, 50)
    view.refresh_dataset_info()

    assert "Train/val: 3/3 par" in view.dataset_info.text()


def test_training_start_exports_with_the_chosen_ratio(qapp, config, settings, monkeypatch):
    """Starten skickar den valda andelen vidare till exporten (TASK-72)."""
    service = DatasetService(config.dataset_dir)
    service.set_classes(["kniv"])
    service.add_samples([
        AnnotatedImage(
            np.full((30, 40, 3), 60, np.uint8),
            [{"class_name": "kniv", "bbox": [2, 2, 8, 8]}],
        )
        for _ in range(2)
    ])
    settings.setValue(TRAIN_RATIO_KEY, 50)
    view = TrainingView(config, service, settings)
    ratios: list = []
    monkeypatch.setattr(service, "export_yolo", lambda root, ratio: ratios.append(ratio))
    monkeypatch.setattr(view.training_service, "create_worker", lambda cfg: None)

    view._on_start()

    assert ratios == [0.5]


def test_training_schedule_is_read_and_written(qapp, settings):
    settings.setValue("training/night_start_hour", 22)
    settings.setValue("training/night_end_hour", 6)
    settings.setValue("training/inactivity_minutes", 45)

    section = TrainingScheduleSection(settings)

    assert section.night_start.value() == 22
    assert section.night_end.value() == 6
    assert section.inactivity.value() == 45

    section.night_start.setValue(21)
    section.night_end.setValue(4)
    section.inactivity.setValue(15)

    assert settings.value("training/night_start_hour", type=int) == 21
    assert settings.value("training/night_end_hour", type=int) == 4
    assert settings.value("training/inactivity_minutes", type=int) == 15
    # träningsvyn läser tiderna som "HH:00" när den köar ett jobb
    assert settings.value("training/night_start") == "21:00"
    assert settings.value("training/night_end") == "04:00"


def test_theme_is_changed_from_the_settings_tab(qapp, window):
    combo = window.settings_view.theme_section.theme_combo
    assert combo.currentData() == current_theme()

    combo.setCurrentIndex(combo.findData("dark"))

    assert window.settings.value("ui/theme") == "dark"
    assert current_theme() == "dark"


def test_dialog_closes_without_changing_anything(qapp, settings):
    settings.setValue("training/night_start_hour", 22)
    settings.setValue("training/inactivity_minutes", 45)
    before = {key: settings.value(key) for key in settings.allKeys()}

    dialog = SettingsDialog(
        "Inställningar – Träning", [TrainingScheduleSection(settings)]
    )
    buttons = dialog.findChild(QDialogButtonBox)
    buttons.button(QDialogButtonBox.StandardButton.Close).click()

    assert dialog.result() == QDialog.DialogCode.Rejected
    assert {key: settings.value(key) for key in settings.allKeys()} == before


def test_settings_button_without_sections_is_disabled(qapp):
    button = settings_button(None, "Inställningar – Test")
    assert not button.isEnabled()
    assert button.text() == "&Inställningar"
