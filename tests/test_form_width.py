"""Maxbredd på formulärfält (TASK-82).

Fälten samlas i ett kort med en maxbredd, så en dropdown eller ett textfält
inte sträcker sig över hela skärmen. Testerna visar fönstret brett och mäter
den faktiska bredden, eftersom det är layouten som ska hålla igen.
"""

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QFormLayout

from xray_detector.domain.config import AppConfig
from xray_detector.ui.main_window import MainWindow
from xray_detector.ui.model_settings import ModelSection
from xray_detector.ui.settings_dialog import (
    DatasetSortSection,
    ThemeSection,
    TrainingScheduleSection,
    TrainValSplitSection,
)
from xray_detector.ui.style import FORM_MAX_WIDTH, LIST_MAX_WIDTH, FormCard

WIDE_WINDOW = (1600, 900)


@pytest.fixture
def config(tmp_path) -> AppConfig:
    config = AppConfig()
    config.data_dir = tmp_path / "data"
    config.models_dir = tmp_path / "models"
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


def _shown_wide(qapp, window, view) -> None:
    """Visar vyn i ett brett fönster; en dold flik behåller sin standardbredd."""
    window.resize(*WIDE_WINDOW)
    window.show()
    window.tabs.setCurrentWidget(view)
    qapp.processEvents()


# --- Kortet (AC 1) ---


def test_form_card_has_a_form_and_a_max_width(qapp):
    card = FormCard("Test")

    assert card.title() == "Test"
    assert card.maximumWidth() == FORM_MAX_WIDTH
    assert isinstance(card.form, QFormLayout)


def test_settings_sections_share_the_form_width(qapp, settings):
    for section in (
        ThemeSection(settings),
        TrainingScheduleSection(settings),
        TrainValSplitSection(settings),
        DatasetSortSection(settings),
    ):
        assert section.maximumWidth() == FORM_MAX_WIDTH, type(section).__name__


def test_model_section_uses_the_list_width(qapp, tmp_path):
    """Knappraden behöver mer plats än ett ensamt formulärfält."""
    section = ModelSection(tmp_path / "models")

    assert section.maximumWidth() == LIST_MAX_WIDTH
    assert LIST_MAX_WIDTH > FORM_MAX_WIDTH


# --- Träningsvyn (AC 2) ---


def test_training_settings_live_in_a_card(qapp, window):
    card = window.training_view.findChild(FormCard)

    assert card is not None
    assert card.title() == "Träningsinställningar"


def test_training_card_stays_narrow_on_a_wide_window(qapp, window):
    _shown_wide(qapp, window, window.training_view)

    card = window.training_view.findChild(FormCard)

    assert card.width() <= FORM_MAX_WIDTH
    assert card.width() < window.training_view.width(), "kortet fyller inte vyn"


def test_training_fields_and_buttons_fit_the_card(qapp, window):
    _shown_wide(qapp, window, window.training_view)
    view = window.training_view

    for widget in (
        view.model_combo,
        view.epochs_spin,
        view.imgsz_spin,
        view.batch_spin,
        view.run_combo,
        view.start_button,
        view.abort_button,
    ):
        assert widget.width() <= FORM_MAX_WIDTH, type(widget).__name__


def test_training_resolution_hint_has_its_own_row(qapp, window):
    """Upplösningslistan klipps inte i ett smalt kort."""
    _shown_wide(qapp, window, window.training_view)
    view = window.training_view
    card = view.findChild(FormCard)

    assert view.imgsz_info.parentWidget() is card
    assert view.imgsz_info.width() <= FORM_MAX_WIDTH


def test_long_dataset_summary_wraps_inside_the_card(qapp, window):
    """En lång sammanställning får inte trycka ut kortet över maxbredden."""
    view = window.training_view
    view.dataset_info.setText(
        "Bilder: 12345  Objekt: 67890  Train/val: 100/20 par  Uppdaterad: 2026-11-13"
    )
    _shown_wide(qapp, window, view)

    card = view.findChild(FormCard)

    assert card.width() <= FORM_MAX_WIDTH
    assert view.dataset_info.width() <= FORM_MAX_WIDTH


# --- Globala inställningar (AC 3, 4) ---


def test_theme_combo_stays_narrow_on_a_wide_window(qapp, window):
    _shown_wide(qapp, window, window.settings_view)

    combo = window.settings_view.theme_section.theme_combo

    assert combo.width() <= FORM_MAX_WIDTH
    assert combo.width() < window.settings_view.width(), "dropdownen fyller inte vyn"


def test_model_list_stays_narrow_on_a_wide_window(qapp, window):
    _shown_wide(qapp, window, window.settings_view)

    section = window.settings_view.model_section

    assert section.width() <= LIST_MAX_WIDTH
    assert section.width() < window.settings_view.width()
