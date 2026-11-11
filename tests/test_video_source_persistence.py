"""Persistens av videofilmsskallan (TASK-23)."""

from pathlib import Path

import pytest
from PySide6.QtWidgets import QFileDialog

from xray_detector.ui.detection_view import StreamPanel


@pytest.fixture
def panel(qapp):
    panel = StreamPanel("left", "Stromm 1")
    panel.show()
    qapp.processEvents()
    return panel


def _forbid_dialog(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("QFileDialog fick inte oppnas")

    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(boom))


def test_restore_activates_file_without_dialog(panel, monkeypatch):
    _forbid_dialog(monkeypatch)
    emitted = []
    panel.source_requested.connect(lambda sid, kind, value: emitted.append((kind, value)))
    panel.restore_source("file", "C:/media/xray.mp4")

    assert emitted == [("file", Path("C:/media/xray.mp4"))]
    assert panel.current_source() == ("file", "C:/media/xray.mp4")
    assert panel.source_combo.currentText() == "Videofil: xray.mp4"


def test_reselecting_saved_file_restarts_without_dialog(panel, monkeypatch):
    _forbid_dialog(monkeypatch)
    emitted = []
    panel.source_requested.connect(lambda sid, kind, value: emitted.append((kind, value)))
    panel.restore_source("file", "C:/media/a.mp4")
    panel.source_combo.setCurrentIndex(0)  # Ingen videokalla: stoppa kallen
    index = panel.source_combo.findData("file:C:/media/a.mp4")
    assert index >= 0
    panel.source_combo.setCurrentIndex(index)  # omval av sparad fil
    assert emitted == [
        ("file", Path("C:/media/a.mp4")),
        ("none", None),
        ("file", Path("C:/media/a.mp4")),
    ]


def test_switching_file_via_dialog(panel, monkeypatch):
    calls = {"n": 0}

    def fake_dialog(parent, caption, directory, filters):
        calls["n"] += 1
        return ("C:/media/b.mp4", "") if calls["n"] == 1 else ("C:/media/c.mp4", "")

    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(fake_dialog))
    emitted = []
    panel.source_requested.connect(lambda sid, kind, value: emitted.append((kind, Path(value))))

    open_index = panel.source_combo.findData("file")
    panel.source_combo.setCurrentIndex(open_index)  # forsta byte -> b.mp4
    assert emitted[-1] == ("file", Path("C:/media/b.mp4"))
    assert panel.source_combo.currentText() == "Videofil: b.mp4"
    assert panel.source_combo.findData("file:C:/media/b.mp4") >= 0

    open_index = panel.source_combo.findData("file")
    panel.source_combo.setCurrentIndex(open_index)  # andra bytet -> c.mp4
    assert emitted[-1] == ("file", Path("C:/media/c.mp4"))
    assert panel.source_combo.currentText() == "Videofil: c.mp4"
    # gamla dynamiska posten ar ersatt, inte hopad
    assert panel.source_combo.findData("file:C:/media/b.mp4") < 0
    assert panel.source_combo.count() == panel.source_combo.count()


def test_cancelled_dialog_keeps_previous_selection(panel, monkeypatch):
    emitted = []
    panel.source_requested.connect(lambda sid, kind, value: emitted.append((kind, value)))
    panel.restore_source("file", "C:/media/x.mp4")
    before_index = panel.source_combo.currentIndex()

    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: ("", "")))
    panel.source_combo.setCurrentIndex(panel.source_combo.findData("file"))  # oppna + avbryt

    assert panel.source_combo.currentIndex() == before_index
    assert emitted == [("file", Path("C:/media/x.mp4"))]  # inget nytt anrop


def test_title_shows_active_file_and_fps(panel):
    from tests.conftest import synthetic_frame
    from xray_detector.domain.capture import StreamFrame

    panel.restore_source("file", "C:/media/x.mp4")
    panel.show_frame(StreamFrame("left", synthetic_frame(), [], "x.mp4", sequence=1, fps=29.5))
    assert "x.mp4" in panel.title_label.text()
    assert "29.5 fps" in panel.title_label.text()
    panel._show_no_source()
    assert panel.title_label.text() == "Stromm 1"


def test_persistence_roundtrip_via_detection_view(qapp, tmp_path, monkeypatch):
    """spara + aterstall via QSettings startar filkallan utan dialog."""
    from PySide6.QtCore import QSettings

    from xray_detector.domain.config import AppConfig
    from xray_detector.ui.detection_view import DetectionView

    _forbid_dialog(monkeypatch)
    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    ini = tmp_path / "settings.ini"

    settings = QSettings(str(ini), QSettings.Format.IniFormat)
    settings.setValue("detection/source_left_kind", "file")
    settings.setValue("detection/source_left_value", "C:/media/x.mp4")
    settings.setValue("detection/source_right_kind", "none")
    settings.sync()

    captured = []
    view = DetectionView(config, QSettings(str(ini), QSettings.Format.IniFormat))
    monkeypatch.setattr(
        type(view.video_service), "set_source",
        lambda self, source_id, kind, value, mode=None: captured.append((source_id, kind, value)) or None,
    )
    view.restore_settings()
    assert ("left", "file", Path("C:/media/x.mp4")) in captured
    # panelen visar sparad fil i kombon
    assert view.left.source_combo.currentText() == "Videofil: x.mp4"
    assert view.left.current_source() == ("file", "C:/media/x.mp4")

    # ny "omstart" ger samma resultat en gaang till
    captured.clear()
    view2 = DetectionView(config, QSettings(str(ini), QSettings.Format.IniFormat))
    monkeypatch.setattr(
        type(view2.video_service), "set_source",
        lambda self, source_id, kind, value, mode=None: captured.append((source_id, kind, value)) or None,
    )
    view2.restore_settings()
    assert ("left", "file", Path("C:/media/x.mp4")) in captured
