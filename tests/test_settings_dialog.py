"""Globala inställningar i fliken och egna inställningar per vy (TASK-43)."""

import threading
from datetime import time

import numpy as np
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QDialog, QDialogButtonBox

from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.infrastructure.dataset_store.store import DatasetStore
from xray_detector.ui.main_window import MainWindow
from xray_detector.ui.model_settings import ModelSection
from xray_detector.ui.settings_dialog import (
    SORT_KEY,
    SORT_NEWEST,
    SORT_OLDEST,
    TRAIN_RATIO_KEY,
    ClassFilterSection,
    DatasetSortSection,
    SettingsDialog,
    TrainingScheduleSection,
    settings_button,
    train_ratio,
)
from xray_detector.ui.style import FormCard
from xray_detector.ui.theme import apply_theme, current_theme
from xray_detector.ui.training_view import TrainingView

# testerna startar MainWindow och tar därför sekunder (TASK-154)
pytestmark = pytest.mark.slow

VIEWS = ("detection_view", "annotation_view", "dataset_view", "training_view")


@pytest.fixture(autouse=True)
def reset_theme(qapp):
    """Temat är globalt: lämna tillbaka det till system efter varje test."""
    yield
    apply_theme(qapp, "system")




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


def test_every_view_has_a_settings_button_with_a_gear(window):
    for name in VIEWS:
        button = getattr(window, name).settings_button
        assert button.text() == "&Inställningar"
        assert not button.icon().isNull(), "kugghjulet ska stå framför texten"
        assert button.shortcut().toString() == "Alt+I"


def test_settings_button_sits_top_right_with_the_theme_toggle_last(window):
    for name in VIEWS:
        view = getattr(window, name)
        row = _top_row(view)
        assert row.itemAt(row.count() - 1).widget() is view.theme_toggle, name
        assert row.itemAt(row.count() - 2).widget() is view.settings_button, name


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


def test_training_settings_open_the_schedule(qapp, window, monkeypatch):
    dialog = _opened_dialog(monkeypatch, window.training_view.settings_button)

    assert dialog.windowTitle() == "Inställningar – Träning"
    assert dialog.findChild(TrainingScheduleSection) is not None


def test_training_settings_only_open_the_schedule(qapp, window, monkeypatch):
    """Andelen train/val flyttades till Dataset-kortet i vyn (TASK-103)."""
    dialog = _opened_dialog(monkeypatch, window.training_view.settings_button)

    assert [type(section) for section in dialog.findChildren(FormCard)] == [
        TrainingScheduleSection
    ]


def test_train_ratio_is_read_and_written(qapp, config, settings):
    assert train_ratio(settings) == 0.8
    view = TrainingView(config, DatasetStore(config.dataset_dir), settings)
    assert view.ratio_spin.value() == 80

    view.ratio_spin.setValue(50)

    assert settings.value(TRAIN_RATIO_KEY, type=int) == 50
    assert train_ratio(settings) == 0.5


def test_dataset_card_holds_the_size_and_the_train_val_ratio(qapp, config, settings):
    """Dataset-kortet samlar storleken och andelen train/val (TASK-103)."""
    view = TrainingView(config, DatasetStore(config.dataset_dir), settings)
    card = view.ratio_spin.parentWidget()

    assert isinstance(card, FormCard)
    assert card.title() == "Dataset"
    assert view.dataset_info.parentWidget() is card


def test_train_ratio_keeps_a_group_on_each_side(qapp, settings):
    """Både train och val får minst en grupp, även om värdet ligger utanför 1-99."""
    settings.setValue(TRAIN_RATIO_KEY, 0)
    assert train_ratio(settings) == 0.01

    settings.setValue(TRAIN_RATIO_KEY, 100)
    assert train_ratio(settings) == 0.99


def test_training_view_shows_train_val_in_pairs(qapp, config, settings):
    """Redovisningen räknar bildpar och följer den valda andelen (TASK-72)."""
    service = DatasetStore(config.dataset_dir)
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
    service = DatasetStore(config.dataset_dir)
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
    monkeypatch.setattr(
        "xray_detector.ui.training_view.export_dataset",
        lambda store, export_dir, family, ratio: ratios.append(ratio)
        or config.export_dir / "yolo" / "data.yaml",
    )
    monkeypatch.setattr(view.training_service, "create_worker", lambda cfg: None)

    view._on_start()
    view.wait_for_export()

    assert ratios == [0.5]


def test_training_start_does_not_block_on_the_export(qapp, config, settings, monkeypatch):
    """Exporten körs i bakgrunden, så _on_start återvänder innan den är klar (TASK-151)."""
    service = DatasetStore(config.dataset_dir)
    service.set_classes(["kniv"])
    service.add_samples([
        AnnotatedImage(
            np.full((30, 40, 3), 60, np.uint8),
            [{"class_name": "kniv", "bbox": [2, 2, 8, 8]}],
        )
        for _ in range(2)
    ])
    view = TrainingView(config, service, settings)
    release = threading.Event()
    monkeypatch.setattr(
        "xray_detector.ui.training_view.export_dataset",
        lambda store, export_dir, family, ratio: release.wait(5)
        or config.export_dir / "yolo" / "data.yaml",
    )
    monkeypatch.setattr(view.training_service, "create_worker", lambda cfg: None)

    view._on_start()

    # anropet är tillbaka medan exporten ännu väntar
    assert view._export_task is not None
    assert not view._export_task.is_done()
    release.set()
    view.wait_for_export()


def test_night_job_uses_the_shared_clock_keys(qapp, config, settings, monkeypatch):
    """Träningsvyn köar nattfönstret med samma "HH:MM"-nycklar som dialogen (TASK-125)."""
    service = DatasetStore(config.dataset_dir)
    service.set_classes(["kniv"])
    service.add_samples([
        AnnotatedImage(
            np.full((30, 40, 3), 60, np.uint8),
            [{"class_name": "kniv", "bbox": [2, 2, 8, 8]}],
        )
        for _ in range(2)
    ])
    settings.setValue("training/night_start", "01:15")
    settings.setValue("training/night_end", "04:45")
    view = TrainingView(config, service, settings)
    monkeypatch.setattr(
        "xray_detector.ui.training_view.export_dataset",
        lambda store, export_dir, family, ratio: config.export_dir / "yolo" / "data.yaml",
    )
    monkeypatch.setattr(view.training_service, "create_worker", lambda cfg: None)
    view.run_combo.setCurrentIndex(view.run_combo.findData("night"))

    view._on_start()

    scheduler = view.training_service.scheduler()
    assert scheduler.has_queued()
    # exporten sparas till starten, inte till klickögonblicket (TASK-151)
    assert scheduler.export is not None
    assert scheduler.night_start == time(1, 15)
    assert scheduler.night_end == time(4, 45)


def test_training_schedule_is_read_and_written(qapp, settings):
    settings.setValue("training/night_start", "22:00")
    settings.setValue("training/night_end", "06:00")
    settings.setValue("training/inactivity_minutes", 45)

    section = TrainingScheduleSection(settings)

    assert section.night_start.value() == 22
    assert section.night_end.value() == 6
    assert section.inactivity.value() == 45

    section.night_start.setValue(21)
    section.night_end.setValue(4)
    section.inactivity.setValue(15)

    assert settings.value("training/inactivity_minutes", type=int) == 15
    # bara "HH:MM"-nyckeln används, av både dialogen och träningsvyn (TASK-125)
    assert settings.value("training/night_start") == "21:00"
    assert settings.value("training/night_end") == "04:00"
    assert settings.value("training/night_start_hour") is None
    assert settings.value("training/night_end_hour") is None


def test_old_night_hour_keys_are_migrated_on_startup(qapp, config):
    """En sparad timme från före TASK-125 blir kvar som "HH:MM" och nyckeln tas bort."""
    settings = QSettings(str(config.data_dir / "settings.ini"), QSettings.Format.IniFormat)
    settings.setValue("training/night_start_hour", 22)
    settings.setValue("training/night_end_hour", 6)
    settings.sync()

    window = MainWindow(config)

    assert window.settings.value("training/night_start") == "22:00"
    assert window.settings.value("training/night_end") == "06:00"
    assert window.settings.value("training/night_start_hour") is None
    assert window.settings.value("training/night_end_hour") is None
    window.detection_view.wait_for_background()
    window.dataset_view.wait_for_refresh()
    window.close()


def test_migration_keeps_an_already_saved_clock(qapp, config):
    """Finns båda nycklarna är "HH:MM"-nyckeln den som gäller."""
    settings = QSettings(str(config.data_dir / "settings.ini"), QSettings.Format.IniFormat)
    settings.setValue("training/night_start", "01:30")
    settings.setValue("training/night_start_hour", 22)
    settings.sync()

    window = MainWindow(config)

    assert window.settings.value("training/night_start") == "01:30"
    assert window.settings.value("training/night_start_hour") is None
    window.detection_view.wait_for_background()
    window.dataset_view.wait_for_refresh()
    window.close()


def test_theme_toggle_switches_between_light_and_dark(qapp, window):
    toggle = window.detection_view.theme_toggle
    apply_theme(qapp, "light")
    toggle.refresh()
    assert toggle.toolTip() == "Byt till mörkt tema"

    toggle.click()

    assert window.settings.value("ui/theme") == "dark"
    assert current_theme() == "dark"
    assert toggle.toolTip() == "Byt till ljust tema"
    # alla vyer följer med, så ikonen visar rätt i varje flik
    assert window.dataset_view.theme_toggle.toolTip() == "Byt till ljust tema"

    toggle.click()

    assert window.settings.value("ui/theme") == "light"
    assert current_theme() == "light"
    assert toggle.toolTip() == "Byt till mörkt tema"


def test_manage_models_opens_the_model_dialog(qapp, window, monkeypatch):
    dialog = _opened_dialog(monkeypatch, window.detection_view.manage_models_button)

    assert dialog.windowTitle() == "Hantera modeller"
    assert dialog.findChild(ModelSection) is window.detection_view.model_section


def test_dialog_closes_without_changing_anything(qapp, settings):
    settings.setValue("training/night_start", "22:00")
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
