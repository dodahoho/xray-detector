"""Enhetsupptäckt (TASK-8): kameranamn via pygrabber, fallback på index."""

import pytest

from xray_detector.infrastructure.video.devices import DeviceInfo, list_devices
from xray_detector.ui.detection_view import StreamPanel


def test_fallback_without_pygrabber(monkeypatch):
    import xray_detector.infrastructure.video.devices as devices

    monkeypatch.setattr(devices, "_windows_device_names", lambda: {})
    result = list_devices()
    assert result == [DeviceInfo(0, "Video 0"), DeviceInfo(1, "Video 1")]


def test_names_from_pygrabber(monkeypatch):
    import xray_detector.infrastructure.video.devices as devices

    monkeypatch.setattr(devices, "_windows_device_names",
                        lambda: {0: "Logitech C920", 1: "Elgato Cam Link", 3: "Annan"})
    result = list_devices()
    assert [(d.index, d.name) for d in result] == [
        (0, "Logitech C920"), (1, "Elgato Cam Link"), (3, "Annan"),
    ]


def test_pygrabber_failure_falls_back(monkeypatch):
    import xray_detector.infrastructure.video.devices as devices

    def boom():
        raise ImportError("pygrabber saknas")

    monkeypatch.setattr(devices, "_windows_device_names", boom)
    assert list_devices() == [DeviceInfo(0, "Video 0"), DeviceInfo(1, "Video 1")]


@pytest.fixture
def panel(qapp, monkeypatch):
    import xray_detector.ui.detection_view as dv

    monkeypatch.setattr(
        "xray_detector.infrastructure.video.devices._windows_device_names",
        lambda: {0: "Logitech C920", 1: "Elgato Cam Link"},
    )
    devices = list_devices()
    panel = StreamPanel("left", "Ström 1", devices)
    panel.show()
    qapp.processEvents()
    return panel


def test_combo_lists_device_names(panel):
    texts = [panel.source_combo.itemText(i) for i in range(panel.source_combo.count())]
    assert "Ingen videokälla" in texts
    assert "UVC 0 · Logitech C920" in texts
    assert "UVC 1 · Elgato Cam Link" in texts
    assert "Öppna videofil..." in texts


def test_selection_emits_uvc_with_index(panel):
    received = []
    panel.source_requested.connect(lambda sid, kind, value, mode=None: received.append((kind, value)))
    index = panel.source_combo.findData("uvc:1")
    panel.source_combo.setCurrentIndex(index)
    assert received[-1] == ("uvc", 1)
    assert panel.current_source() == ("uvc", 1)


def test_restore_source_uses_item_data(panel):
    panel.restore_source("uvc", 0)
    assert panel.source_combo.currentData() == "uvc:0"


def test_fallback_devices_still_work(qapp):
    panel = StreamPanel("right", "Ström 2")  # inga enheter angivna
    texts = [panel.source_combo.itemText(i) for i in range(panel.source_combo.count())]
    assert "Ingen videokälla" in texts and "Öppna videofil..." in texts
