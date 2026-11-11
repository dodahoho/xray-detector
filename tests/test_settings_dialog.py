"""Globala inställningar i fliken och egna inställningar per vy (TASK-43)."""

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QDialog, QDialogButtonBox

from xray_detector.domain.config import AppConfig
from xray_detector.ui.main_window import MainWindow
from xray_detector.ui.settings_dialog import (
    SettingsDialog,
    ThemeSection,
    TrainingScheduleSection,
    settings_button,
)
from xray_detector.ui.theme import apply_theme, current_theme

VIEWS = ("detection_view", "annotation_view", "dataset_view", "training_view")


@pytest.fixture(autouse=True)
def reset_theme(qapp):
    """Temat är globalt: lämna tillbaka det till system efter varje test."""
    yield
    apply_theme(qapp, "system")


@pytest.fixture
def config(tmp_path) -> AppConfig:
    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    return config


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
    assert window.tabs.tabText(4) == "&Inställningar"
    assert window.tabs.widget(4) is window.settings_view
    assert isinstance(window.settings_view.theme_section, ThemeSection)


def test_tab_row_has_five_tabs(window):
    assert [window.tabs.tabText(index) for index in range(5)] == [
        "&Detektion",
        "&Annotation",
        "Data&set",
        "&Träning",
        "&Inställningar",
    ]


def test_every_view_has_a_settings_button_with_a_gear(window):
    for name in VIEWS:
        button = getattr(window, name).settings_button
        assert button.text() == "&Vyns inställningar"
        assert not button.icon().isNull(), "kugghjulet ska stå framför texten"
        assert button.shortcut().toString() == "Alt+V"


def test_settings_button_sits_top_right_in_every_view(window):
    for name in VIEWS:
        view = getattr(window, name)
        row = _top_row(view)
        assert row.itemAt(row.count() - 1).widget() is view.settings_button, name


def test_view_without_own_settings_keeps_a_disabled_button(window):
    for name in ("detection_view", "annotation_view", "dataset_view"):
        button = getattr(window, name).settings_button
        assert not button.isEnabled(), name
        assert button.toolTip() == "Vyn har inga egna inställningar"

    assert window.training_view.settings_button.isEnabled()


def test_training_settings_open_the_schedule(qapp, window, monkeypatch):
    dialog = _opened_dialog(monkeypatch, window.training_view.settings_button)

    assert dialog.windowTitle() == "Inställningar – Träning"
    assert dialog.findChild(TrainingScheduleSection) is not None
    assert dialog.findChild(ThemeSection) is None, "temat hör till inställningsfliken"


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
    assert button.text() == "&Vyns inställningar"
