"""Ateranslutningsknapp perstrompanel (TASK-19)."""

from types import SimpleNamespace

import pytest

from xray_detector.ui.detection_view import StreamPanel


@pytest.fixture
def panel(qapp):
    panel = StreamPanel("left", "Stromm 1")
    panel.show()
    qapp.processEvents()
    return panel


def set_active(panel, kind, value):
    panel._active = (kind, value)


def test_first_loss_auto_retries_without_button(panel, monkeypatch):
    emitted = []
    panel.source_requested.connect(lambda sid, kind, value: emitted.append((kind, value)))
    timers = []
    monkeypatch.setattr("xray_detector.ui.detection_view.QTimer.singleShot",
                        lambda ms, fn: timers.append((ms, fn)))
    set_active(panel, "uvc", 0)
    panel.show_source_lost()
    assert panel.lost_widget.isVisible()
    assert not panel.retry_button.isVisible()
    assert "f\u00f6rs\u00f6k 1/3" in panel.lost_label.text()
    assert timers, "automatiskt aterforsok schemalades inte"
    timers[0][1]()  # utlos timern
    assert emitted == [("uvc", 0)], "aterforsoket emitterar senaste kallval"


def test_after_max_retries_button_appears(panel, monkeypatch):
    emitted = []
    panel.source_requested.connect(lambda sid, kind, value: emitted.append((kind, value)))
    monkeypatch.setattr("xray_detector.ui.detection_view.QTimer.singleShot",
                        lambda ms, fn: emitted.append(("timer", ms)))
    set_active(panel, "uvc", 1)
    panel.show_source_lost()  # forsok 1 (auto)
    panel.show_source_lost()  # forsok 2 (auto)
    panel.show_source_lost()  # forsok 3 -> knapp
    assert panel.retry_button.isVisible()
    assert "3" in panel.lost_label.text()
    auto = [e for e in emitted if e[0] == "timer"]
    assert len(auto) == 2
    panel.retry_button.click()
    assert emitted[-1] == ("uvc", 1)


def test_incoming_frame_resets_connection_state(panel):
    from tests.conftest import synthetic_frame
    from xray_detector.domain.capture import StreamFrame

    set_active(panel, "uvc", 0)
    panel.show_source_lost()
    panel.show_frame(StreamFrame("left", synthetic_frame(), [], "kamera", sequence=1))
    assert panel._lost_attempts == 0
    assert panel.display.isVisible()
    assert not panel.lost_widget.isVisible()


def test_retry_without_source_keeps_message(panel):
    set_active(panel, "none", None)
    panel.show_source_lost()
    panel.show_source_lost()
    panel.show_source_lost()
    panel.retry_button.click()
    # ingen kalla aktiv: meddelandet stannar, inget anrop emitteras
    assert panel.lost_widget.isVisible()


def test_detection_view_routes_source_lost_to_panel(qapp):
    from xray_detector.domain.config import AppConfig
    from xray_detector.ui.detection_view import DetectionView
    from PySide6.QtCore import QSettings

    import tempfile
    from pathlib import Path

    tmp = Path(tempfile.mkdtemp())
    config = AppConfig()
    config.data_dir = tmp
    config.ensure_dirs()
    view = DetectionView(config, QSettings(str(tmp / "s.ini"), QSettings.Format.IniFormat))
    monkey_target = SimpleNamespace(_lost_attempts=0)
    view._on_source_lost("left")
    assert view.left._lost_attempts == 1
