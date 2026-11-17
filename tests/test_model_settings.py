"""Modellsektionen i de globala inställningarna (TASK-81, TASK-115)."""

import json
import urllib.request
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
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


def _write_run(trained_dir: Path, run: str = "v3") -> Path:
    """Skapar en träningskörning med manifest och vikter, som train_task gör."""
    run_dir = trained_dir / run
    weights = run_dir / "yolo26m" / "weights" / "best.pt"
    weights.parent.mkdir(parents=True, exist_ok=True)
    weights.write_bytes(b"vikter")
    manifest = {
        "base_weights": "yolo26m.pt",
        "weights_relative": "yolo26m/weights/best.pt",
        "classes": ["kniv"],
        "family": "yolo",
        "name": "Vår tränade modell",
    }
    (run_dir / "training_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    return weights


@pytest.fixture
def trained_config(config) -> AppConfig:
    """Konfiguration med en genomförd träningskörning under models/trained/."""
    _write_run(config.trained_dir)
    return config


@pytest.fixture
def trained_window(qapp, trained_config):
    window = MainWindow(trained_config)
    yield window
    window.detection_view.wait_for_background()
    window.dataset_view.wait_for_refresh()
    window.close()


def _keys(section: ModelSection) -> list[str]:
    return [
        section.list.item(row).data(Qt.ItemDataRole.UserRole)
        for row in range(section.list.count())
    ]


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


def test_the_address_dialog_shows_an_example(section, monkeypatch):
    """Dialogen har ingen egen hjälptext, så instruktionen står i etiketten."""
    opened: list = []

    def capture(parent, title, label, *args, **kwargs):
        opened.append((title, label))
        return ("", False)

    monkeypatch.setattr(QInputDialog, "getText", capture)

    section.add_url_button.click()

    title, label = opened[0]
    assert title == "Lägg till modell från internet"
    assert "https://huggingface.co/Ultralytics/YOLO26/resolve/main/yolo26l.pt" in label
    assert ".pt" in label and ".pth" in label
    assert "nedladdningslänk" in label


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


# --- Egentränade modeller (TASK-115) ---


def test_trained_models_are_listed_in_the_settings_tab(qapp, trained_config):
    section = ModelSection(trained_config.models_dir, trained_config.trained_dir)

    assert _keys(section) == [spec.key for spec in MODEL_SPECS] + ["trained-v3"]
    assert section.list.item(section.list.count() - 1).text() == "Vår tränade modell"


def test_trained_model_is_read_only_in_the_settings_tab(qapp, trained_config):
    section = ModelSection(trained_config.models_dir, trained_config.trained_dir)
    section.list.setCurrentRow(section.list.count() - 1)

    assert section.current_key() == "trained-v3"
    assert not section.rename_button.isEnabled()
    assert not section.remove_button.isEnabled()
    assert section.trained_hint.isVisibleTo(section)


def test_base_model_is_editable_again_after_a_trained_one(qapp, trained_config):
    section = ModelSection(trained_config.models_dir, trained_config.trained_dir)
    section.list.setCurrentRow(section.list.count() - 1)
    section.list.setCurrentRow(0)

    assert section.rename_button.isEnabled()
    assert section.remove_button.isEnabled()
    assert not section.trained_hint.isVisibleTo(section)


def test_removing_a_base_model_keeps_the_trained_models(qapp, trained_config):
    section = ModelSection(trained_config.models_dir, trained_config.trained_dir)
    section.list.setCurrentRow(0)

    section.remove_button.click()

    assert _keys(section) == [spec.key for spec in MODEL_SPECS[1:]] + ["trained-v3"]


def test_settings_list_and_detection_combo_show_the_same_models(trained_window):
    """Samma lista överallt: väljaren och inställningarna visar samma modeller."""
    section = trained_window.settings_view.model_section
    combo = trained_window.detection_view.model_combo

    assert _keys(section) == [combo.itemData(row) for row in range(combo.count())]
    assert "trained-v3" in _keys(section)
