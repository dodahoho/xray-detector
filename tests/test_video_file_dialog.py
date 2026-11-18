"""Förvald katalog i filväljaren för videofiler (TASK-85)."""

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QFileDialog

from xray_detector.domain.config import PROJECT_ROOT
from xray_detector.ui.stream_panel import StreamPanel
from xray_detector.ui.video_file_dialog import (
    DEFAULT_DIR,
    DIR_KEY,
    remember_video_file,
    video_file_dir,
)

MEDIA_DIR = PROJECT_ROOT / "media"




@pytest.fixture
def panel(qapp, settings):
    panel = StreamPanel("left", settings=settings)
    panel.show()
    qapp.processEvents()
    return panel


def _fake_dialog(monkeypatch, chosen):
    """Fejkar filväljaren och samlar katalogargumentet för varje anrop."""
    seen = []

    def fake_dialog(parent, caption, directory, filters):
        seen.append(directory)
        return chosen, ""

    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(fake_dialog))
    return seen


def _open_file_dialog(panel):
    panel.source_combo.setCurrentIndex(panel.source_combo.findData("file"))


def test_default_dir_is_media(settings):
    assert DEFAULT_DIR == MEDIA_DIR
    assert video_file_dir(settings) == str(MEDIA_DIR)


def test_dialog_opens_in_media(panel, monkeypatch):
    seen = _fake_dialog(monkeypatch, "")
    _open_file_dialog(panel)
    assert seen == [str(MEDIA_DIR)]


def test_chosen_dir_is_remembered(panel, monkeypatch, tmp_path):
    other = tmp_path / "filmer"
    other.mkdir()
    chosen = other / "x.mp4"
    seen = _fake_dialog(monkeypatch, str(chosen))

    _open_file_dialog(panel)
    assert panel.current_source() == ("file", str(chosen))
    assert video_file_dir(panel.settings) == str(other)

    # nästa dialog öppnas i samma katalog i stället för media/
    _open_file_dialog(panel)
    assert seen == [str(MEDIA_DIR), str(other)]


def test_cancelled_dialog_keeps_remembered_dir(panel, monkeypatch, tmp_path):
    other = tmp_path / "filmer"
    other.mkdir()
    remember_video_file(panel.settings, other / "x.mp4")
    _fake_dialog(monkeypatch, "")

    _open_file_dialog(panel)
    assert video_file_dir(panel.settings) == str(other)


def test_missing_saved_dir_falls_back_to_media(settings, tmp_path):
    settings.setValue(DIR_KEY, str(tmp_path / "borta"))
    assert video_file_dir(settings) == str(MEDIA_DIR)


def test_remembered_dir_survives_restart(tmp_path):
    ini = tmp_path / "settings.ini"
    other = tmp_path / "filmer"
    other.mkdir()
    first = QSettings(str(ini), QSettings.Format.IniFormat)
    remember_video_file(first, other / "x.mp4")
    first.sync()

    second = QSettings(str(ini), QSettings.Format.IniFormat)
    assert video_file_dir(second) == str(other)


def test_panel_without_settings_uses_media(qapp, monkeypatch):
    seen = _fake_dialog(monkeypatch, "")
    panel = StreamPanel("left")
    panel.show()
    qapp.processEvents()

    _open_file_dialog(panel)
    assert seen == [str(MEDIA_DIR)]
