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


def test_video_mode_roundtrip_in_settings(tmp_path):
    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    assert load_video_mode(settings) is None

    save_video_mode(settings, VideoMode(1920, 1080, "MJPG"))
    assert load_video_mode(settings) == VideoMode(1920, 1080, "MJPG")

    clear_video_mode(settings)
    assert load_video_mode(settings) is None


@pytest.fixture
def settings(tmp_path):
    return QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)


@pytest.fixture
def settings_view(qapp, settings, raw_formats):
    from xray_detector.ui.settings_view import SettingsView

    view = SettingsView(settings, [DeviceInfo(0, "USB Video")])
    view._reload_video_modes()
    return view


def test_settings_lists_device_resolutions_and_formats(settings_view):
    resolutions = [
        settings_view.video_resolution.itemText(i)
        for i in range(settings_view.video_resolution.count())
    ]
    assert resolutions == ["Auto (drivrutinen väljer)", "1920x1080", "1280x720"]

    settings_view.video_resolution.setCurrentIndex(
        settings_view.video_resolution.findData("1920x1080")
    )
    formats = [
        settings_view.video_format.itemText(i)
        for i in range(settings_view.video_format.count())
    ]
    assert formats == ["MJPG", "YUY2"]


def test_settings_saves_choice(settings_view, settings):
    settings_view.video_resolution.setCurrentIndex(
        settings_view.video_resolution.findData("1280x720")
    )
    settings_view.video_format.setCurrentIndex(
        settings_view.video_format.findData("MJPG")
    )

    assert load_video_mode(settings) == VideoMode(1280, 720, "MJPG")


def test_settings_auto_clears_choice(settings_view, settings):
    settings_view.video_resolution.setCurrentIndex(
        settings_view.video_resolution.findData("1920x1080")
    )
    assert load_video_mode(settings) is not None

    settings_view.video_resolution.setCurrentIndex(0)

    assert load_video_mode(settings) is None
    assert not settings_view.video_format.isEnabled()


def test_settings_restores_saved_choice(qapp, settings, raw_formats):
    from xray_detector.ui.settings_view import SettingsView

    save_video_mode(settings, VideoMode(1280, 720, "MJPG"))
    view = SettingsView(settings, [DeviceInfo(0, "USB Video")])
    view._reload_video_modes()

    assert view.video_resolution.currentData() == "1280x720"
    assert view.video_format.currentData() == "MJPG"


def test_detection_view_passes_saved_mode(qapp, tmp_path, settings, monkeypatch):
    from xray_detector.domain.config import AppConfig
    from xray_detector.ui.detection_view import DetectionView

    save_video_mode(settings, VideoMode(1280, 720, "MJPG"))
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

    view._on_source_requested("left", "uvc", 0)

    assert captured == [VideoMode(1280, 720, "MJPG")]
