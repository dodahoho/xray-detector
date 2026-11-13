"""Modellsektionen i de globala inställningarna (TASK-81)."""

import urllib.request

import pytest
from PySide6.QtWidgets import QFileDialog, QInputDialog

from xray_detector.application.model_registry import MODEL_SPECS
from xray_detector.domain.config import AppConfig
from xray_detector.ui.main_window import MainWindow
from xray_detector.ui.model_settings import ModelSection


class _FakeResponse:
    """Svar från urlopen utan nätverk."""

    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> bool:
        return False


@pytest.fixture
def config(tmp_path) -> AppConfig:
    """Egen models_dir, så testerna aldrig rör projektets models/."""
    config = AppConfig()
    config.data_dir = tmp_path / "data"
    config.models_dir = tmp_path / "models"
    config.ensure_dirs()
    return config


@pytest.fixture
def window(qapp, config):
    window = MainWindow(config)
    yield window
    window.detection_view.wait_for_background()
    window.dataset_view.wait_for_refresh()
    window.close()


@pytest.fixture
def section(qapp, config) -> ModelSection:
    return ModelSection(config.models_dir)


def _choose_file(monkeypatch, path) -> None:
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", lambda *args, **kwargs: (str(path), "")
    )


def _answer(monkeypatch, text: str) -> None:
    monkeypatch.setattr(
        QInputDialog, "getText", lambda *args, **kwargs: (text, True)
    )


# --- Listan (AC 2) ---


def test_settings_tab_lists_the_models(window):
    section = window.settings_view.model_section

    assert section.list.count() == len(MODEL_SPECS)
    assert section.list.item(0).text() == MODEL_SPECS[0].label
    assert section.current_key() == MODEL_SPECS[0].key


def test_list_shows_the_weights_in_the_tooltip(section):
    assert MODEL_SPECS[0].weights in section.list.item(0).toolTip()


def test_buttons_need_a_selection(section):
    section.catalog.save([])
    section.refresh()

    assert not section.rename_button.isEnabled()
    assert not section.remove_button.isEnabled()


# --- Lägga till (AC 3, 4) ---


def test_adding_a_file_adds_it_to_the_list(section, tmp_path, monkeypatch):
    source = tmp_path / "min-modell.pt"
    source.write_bytes(b"vikter")
    _choose_file(monkeypatch, source)

    section.add_file_button.click()
    section.wait_for_download()

    assert section.list.count() == len(MODEL_SPECS) + 1
    assert section.list.item(section.list.count() - 1).text() == "min-modell"
    assert section.current_key() == "min-modell"
    assert "Tillagd: min-modell" in section.status.text()


def test_adding_from_an_address_downloads_the_model(section, monkeypatch):
    _answer(monkeypatch, "https://example.com/vikter/egen.pt")
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda url, timeout: _FakeResponse(b"nedladdad")
    )

    section.add_url_button.click()
    section.wait_for_download()

    assert (section.catalog.models_dir / "egen.pt").read_bytes() == b"nedladdad"
    assert section.current_key() == "egen"


def test_a_failed_download_is_reported(section, monkeypatch):
    _answer(monkeypatch, "https://example.com/vikter/")

    section.add_url_button.click()
    section.wait_for_download()

    assert "Kunde inte lägga till modellen" in section.status.text()
    assert section.list.count() == len(MODEL_SPECS)


# --- Byt namn och ta bort (AC 5, 6) ---


def test_rename_changes_the_label_in_the_list(section, monkeypatch):
    _answer(monkeypatch, "Vår modell")

    section.rename_button.click()

    assert section.list.item(0).text() == "Vår modell"
    assert section.current_key() == MODEL_SPECS[0].key, "nyckeln är oförändrad"


def test_remove_takes_the_model_out_of_the_list(section):
    section.remove_button.click()

    assert section.list.count() == len(MODEL_SPECS) - 1
    assert section.current_key() == MODEL_SPECS[1].key


# --- Väljarna följer listan (AC 7) ---


def test_changed_list_updates_both_model_combos(window, tmp_path, monkeypatch):
    source = tmp_path / "min-modell.pt"
    source.write_bytes(b"vikter")
    _choose_file(monkeypatch, source)
    section = window.settings_view.model_section

    section.add_file_button.click()
    section.wait_for_download()

    for combo in (
        window.detection_view.model_combo,
        window.training_view.model_combo,
    ):
        labels = [combo.itemText(row) for row in range(combo.count())]
        assert "min-modell" in labels


def test_removed_model_leaves_both_model_combos(window):
    section = window.settings_view.model_section
    section.list.setCurrentRow(0)
    removed = section.current_key()

    section.remove_button.click()

    for combo in (
        window.detection_view.model_combo,
        window.training_view.model_combo,
    ):
        keys = [combo.itemData(row) for row in range(combo.count())]
        assert removed not in keys
