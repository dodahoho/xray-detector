"""Inställningar per flik i stället för inställningsflik (TASK-43)."""

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QDialog, QDialogButtonBox

from xray_detector.domain.config import AppConfig
from xray_detector.ui.main_window import MainWindow
from xray_detector.ui.settings_dialog import (
    SettingsDialog,
    ThemeSection,
    TrainingScheduleSection,
)
from xray_detector.ui.theme import apply_theme, current_theme


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


def _opened_dialog(monkeypatch, button) -> SettingsDialog:
    """Klickar på knappen och fångar dialogen i stället för att öppna den modalt."""
    opened: list = []
    monkeypatch.setattr(SettingsDialog, "exec", lambda self: opened.append(self))
    button.click()
    assert len(opened) == 1
    return opened[0]


def test_tab_row_has_four_tabs(window):
    assert window.tabs.count() == 4
    assert [window.tabs.tabText(index) for index in range(4)] == [
        "&Detektion",
        "&Annotation",
        "Data&set",
        "&Träning",
    ]


def test_every_view_has_a_settings_button(window):
    views = (
        window.detection_view,
        window.annotation_view,
        window.dataset_view,
        window.training_view,
    )
    for view in views:
        assert view.settings_button.text() == "&Inställningar"
        assert view.settings_button.shortcut().toString() == "Alt+I"


def test_settings_button_opens_the_views_dialog(qapp, window, monkeypatch):
    dialog = _opened_dialog(monkeypatch, window.training_view.settings_button)

    assert dialog.windowTitle() == "Inställningar – Träning"
    assert dialog.findChild(TrainingScheduleSection) is not None
    assert dialog.findChild(ThemeSection) is not None


def test_view_without_own_settings_shows_the_global_theme(qapp, window, monkeypatch):
    dialog = _opened_dialog(monkeypatch, window.detection_view.settings_button)

    assert dialog.windowTitle() == "Inställningar – Detektion"
    assert dialog.findChild(TrainingScheduleSection) is None
    assert dialog.findChild(ThemeSection) is not None


def test_training_schedule_is_reachable_from_the_training_view(qapp, settings):
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


def test_theme_can_still_be_changed(qapp, settings):
    section = ThemeSection(settings)
    assert section.theme_combo.currentData() == current_theme()

    section.theme_combo.setCurrentIndex(section.theme_combo.findData("dark"))

    assert settings.value("ui/theme") == "dark"
    assert current_theme() == "dark"


def test_dialog_closes_without_changing_anything(qapp, settings):
    settings.setValue("ui/theme", "light")
    settings.setValue("training/night_start_hour", 22)
    settings.setValue("training/inactivity_minutes", 45)
    before = {key: settings.value(key) for key in settings.allKeys()}

    dialog = SettingsDialog(
        "Inställningar – Träning",
        [TrainingScheduleSection(settings), ThemeSection(settings)],
    )
    buttons = dialog.findChild(QDialogButtonBox)
    buttons.button(QDialogButtonBox.StandardButton.Close).click()

    assert dialog.result() == QDialog.DialogCode.Rejected
    assert {key: settings.value(key) for key in settings.allKeys()} == before
