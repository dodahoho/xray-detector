"""UVC-enheternas upplösningar och format, samt valet av dem (TASK-39)."""

import cv2
import pytest
from PySide6.QtCore import QSettings

from xray_detector.domain.capture import VideoMode
from xray_detector.infrastructure.video.devices import DeviceInfo, list_device_modes
from xray_detector.infrastructure.video.source import UvcSource
from xray_detector.ui.video_settings import (
    clear_video_mode,
    load_video_mode,
    save_video_mode,
)

RAW_FORMATS = [
    {"width": 1920, "height": 1080, "media_type_str": "MJPG"},
    {"width": 1920, "height": 1080, "media_type_str": "MJPG"},  # dubblett
    {"width": 1920, "height": 1080, "media_type_str": "YUY2"},
    {"width": 1280, "height": 720, "media_type_str": "MJPG"},
]


@pytest.fixture
def raw_formats(monkeypatch):
    import xray_detector.infrastructure.video.devices as devices

    monkeypatch.setattr(devices, "_windows_device_formats", lambda index: RAW_FORMATS)


@pytest.fixture
def settings(tmp_path):
    return QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)


def test_modes_are_deduplicated_in_device_order(raw_formats):
    assert list_device_modes(0) == [
        VideoMode(1920, 1080, "MJPG"),
        VideoMode(1920, 1080, "YUY2"),
        VideoMode(1280, 720, "MJPG"),
    ]


def test_modes_are_empty_without_pygrabber(monkeypatch):
    import xray_detector.infrastructure.video.devices as devices

    monkeypatch.setattr(devices, "_windows_device_formats", lambda index: [])
    assert list_device_modes(0) == []


def test_mode_label():
    assert VideoMode(1920, 1080, "MJPG").label == "1920x1080 MJPG"
    assert VideoMode(640, 480).label == "640x480"


def test_open_params_request_format_and_resolution():
    """Formatet måste anges vid öppning; cap.set(FOURCC) ignoreras av DSHOW."""
    source = UvcSource(0, VideoMode(1920, 1080, "MJPG"))

    assert source._open_params() == [
        cv2.CAP_PROP_FOURCC,
        cv2.VideoWriter_fourcc(*"MJPG"),
        cv2.CAP_PROP_FRAME_WIDTH,
        1920,
        cv2.CAP_PROP_FRAME_HEIGHT,
        1080,
    ]


def test_open_params_without_mode_keeps_driver_default():
    assert UvcSource(0)._open_params() == []


def test_open_params_skip_fourcc_for_non_fourcc_names():
    """Virtuella kameror rapporterar RGB24/ARGB32 som inte är fyra tecken."""
    params = UvcSource(1, VideoMode(1280, 720, "RGB24"))._open_params()

    assert cv2.CAP_PROP_FOURCC not in params
    assert params == [
        cv2.CAP_PROP_FRAME_WIDTH,
        1280,
        cv2.CAP_PROP_FRAME_HEIGHT,
        720,
    ]


def test_source_passes_params_to_videocapture(monkeypatch):
    calls = []

    class _FakeCapture:
        def isOpened(self):
            return True

        def set(self, *_args):
            return True

        def release(self):
            pass

    def fake_capture(*args):
        calls.append(args)
        return _FakeCapture()

    monkeypatch.setattr(cv2, "VideoCapture", fake_capture)
    source = UvcSource(0, VideoMode(1920, 1080, "MJPG"))
    source._open()

    assert calls[0][0] == 0
    assert calls[0][1] == cv2.CAP_DSHOW
    assert cv2.VideoWriter_fourcc(*"MJPG") in calls[0][2]


def test_video_service_forwards_mode(monkeypatch):
    from xray_detector.application.video_service import VideoService

    created = []
    monkeypatch.setattr(
        "xray_detector.application.video_service.UvcSource",
        lambda index, mode=None: created.append((index, mode)) or None,
    )
    service = VideoService()
    monkeypatch.setattr(service.camera_service, "set_source", lambda *args: None)

    service.set_source("left", "uvc", 1, VideoMode(1280, 720, "MJPG"))

    assert created == [(1, VideoMode(1280, 720, "MJPG"))]


def test_video_mode_roundtrip_per_panel(settings):
    assert load_video_mode(settings, "left") is None

    save_video_mode(settings, "left", VideoMode(1920, 1080, "MJPG"))
    save_video_mode(settings, "right", VideoMode(1280, 720, "YUY2"))

    assert load_video_mode(settings, "left") == VideoMode(1920, 1080, "MJPG")
    assert load_video_mode(settings, "right") == VideoMode(1280, 720, "YUY2")

    clear_video_mode(settings, "left")
    assert load_video_mode(settings, "left") is None
    assert load_video_mode(settings, "right") == VideoMode(1280, 720, "YUY2")


@pytest.fixture
def panel(qapp, settings, raw_formats):
    from xray_detector.ui.detection_view import StreamPanel

    panel = StreamPanel("left", "Ström 1", [DeviceInfo(0, "USB Video")], settings)
    emitted = []
    panel.source_requested.connect(
        lambda sid, kind, value, mode=None: emitted.append((kind, value, mode))
    )
    panel.emitted = emitted
    return panel


def _select_uvc(panel, index=0):
    panel.source_combo.setCurrentIndex(panel.source_combo.findData(f"uvc:{index}"))


def test_panel_hides_mode_controls_until_uvc_selected(panel):
    assert not panel.resolution_combo.isVisibleTo(panel)
    assert not panel.format_combo.isVisibleTo(panel)

    _select_uvc(panel)

    assert panel.resolution_combo.isVisibleTo(panel)
    assert panel.format_combo.isVisibleTo(panel)


def test_panel_lists_device_modes(panel):
    _select_uvc(panel)

    resolutions = [
        panel.resolution_combo.itemText(i)
        for i in range(panel.resolution_combo.count())
    ]
    assert resolutions == ["Auto", "1920x1080", "1280x720"]

    panel.resolution_combo.setCurrentIndex(
        panel.resolution_combo.findData("1920x1080")
    )
    formats = [
        panel.format_combo.itemText(i) for i in range(panel.format_combo.count())
    ]
    assert formats == ["MJPG", "YUY2"]


def test_panel_emits_mode_with_source_request(panel):
    _select_uvc(panel)
    assert panel.emitted[-1] == ("uvc", 0, None)

    panel.resolution_combo.setCurrentIndex(
        panel.resolution_combo.findData("1920x1080")
    )
    assert panel.emitted[-1] == ("uvc", 0, VideoMode(1920, 1080, "MJPG"))

    panel.format_combo.setCurrentIndex(panel.format_combo.findData("YUY2"))
    assert panel.emitted[-1] == ("uvc", 0, VideoMode(1920, 1080, "YUY2"))


def test_panel_saves_and_restores_mode(qapp, settings, raw_formats):
    from xray_detector.ui.detection_view import StreamPanel

    save_video_mode(settings, "left", VideoMode(1280, 720, "MJPG"))
    panel = StreamPanel("left", "Ström 1", [DeviceInfo(0, "USB Video")], settings)
    emitted = []
    panel.source_requested.connect(
        lambda sid, kind, value, mode=None: emitted.append(mode)
    )

    _select_uvc(panel)

    assert panel.resolution_combo.currentData() == "1280x720"
    assert panel.format_combo.currentData() == "MJPG"
    assert emitted[-1] == VideoMode(1280, 720, "MJPG")


def test_panel_auto_clears_saved_mode(panel, settings):
    _select_uvc(panel)
    panel.resolution_combo.setCurrentIndex(
        panel.resolution_combo.findData("1920x1080")
    )
    assert load_video_mode(settings, "left") is not None

    panel.resolution_combo.setCurrentIndex(0)

    assert load_video_mode(settings, "left") is None
    assert panel.emitted[-1] == ("uvc", 0, None)


def test_panel_hides_mode_controls_for_file_source(panel, tmp_path):
    _select_uvc(panel)
    assert panel.resolution_combo.isVisibleTo(panel)

    panel._activate_file(tmp_path / "klipp.mp4")

    assert not panel.resolution_combo.isVisibleTo(panel)
    assert panel.emitted[-1][2] is None


def test_detection_view_passes_panel_mode(qapp, tmp_path, settings, raw_formats, monkeypatch):
    from xray_detector.domain.config import AppConfig
    from xray_detector.ui.detection_view import DetectionView

    monkeypatch.setattr(
        "xray_detector.application.video_service.VideoService.list_devices",
        staticmethod(lambda: [DeviceInfo(0, "USB Video")]),
    )
    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    view = DetectionView(config, settings)
    captured = []
    monkeypatch.setattr(
        view.video_service,
        "set_source",
        lambda source_id, kind, value, mode=None: captured.append(mode) or None,
    )

    _select_uvc(view.left)
    view.left.resolution_combo.setCurrentIndex(
        view.left.resolution_combo.findData("1920x1080")
    )
    view.left.format_combo.setCurrentIndex(view.left.format_combo.findData("MJPG"))

    assert captured[-1] == VideoMode(1920, 1080, "MJPG")
