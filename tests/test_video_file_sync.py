"""Synkad uppspelning av två videofiler (TASK-171).

Filerna väljs för att visa samma förlopp från två vinklar, så när en fil väljs
i en panel ska den andra panelens fil startas om från början med samma
starttid. Bara filkällor påverkas; en UVC-kamera rörs inte.
"""

import time
from pathlib import Path

import pytest
from PySide6.QtCore import Qt, QTimer

from xray_detector.infrastructure.video.camera_service import StreamWorker
from xray_detector.infrastructure.video.devices import DeviceInfo
from xray_detector.infrastructure.video.source import FileSource, build_source


def wait_for(qapp, predicate, timeout_ms=8000, step_ms=25):
    elapsed = 0
    while elapsed < timeout_ms:
        qapp.processEvents()
        if predicate():
            return True
        QTimer.singleShot(step_ms, lambda: None)
        time.sleep(step_ms / 1000)
        elapsed += step_ms
    return False


def test_build_source_forwards_shared_start(monkeypatch):
    import xray_detector.infrastructure.video.source as source_module

    created = []
    monkeypatch.setattr(
        source_module,
        "FileSource",
        lambda path, start_at=None: created.append((path, start_at)) or None,
    )

    build_source("file", "C:/media/a.mp4", None, 12.5)

    assert created == [(Path("C:/media/a.mp4"), 12.5)]


def test_file_source_waits_for_shared_start(video_file):
    """Första ramen läses inte förrän den gemensamma starttiden har passerat."""
    start_at = time.perf_counter() + 0.2
    source = FileSource(video_file, start_at)
    source.open()
    try:
        assert source.read() is not None
        assert time.perf_counter() >= start_at
    finally:
        source.close()


def test_workers_with_shared_start_emit_first_frame_together(qapp, video_file):
    """Den andra arbetaren startar senare men första ramen kommer ändå samtidigt."""
    start_at = time.perf_counter() + 0.3
    left = StreamWorker("left", FileSource(video_file, start_at))
    right = StreamWorker("right", FileSource(video_file, start_at))
    stamps = {}
    # direkt anslutning: tidsstämpeln sätts i arbetstråden, inte när vyn råkar
    # läsa kön
    left.frame_ready.connect(
        lambda _frame: stamps.setdefault("left", time.perf_counter()),
        Qt.ConnectionType.DirectConnection,
    )
    right.frame_ready.connect(
        lambda _frame: stamps.setdefault("right", time.perf_counter()),
        Qt.ConnectionType.DirectConnection,
    )
    left.start()
    time.sleep(0.1)
    right.start()
    try:
        assert wait_for(qapp, lambda: len(stamps) == 2), "båda strömmarna gav ingen ram"
    finally:
        left.stop()
        right.stop()

    assert abs(stamps["left"] - stamps["right"]) < 0.05


@pytest.fixture
def view(qapp, tmp_path, settings, monkeypatch):
    from xray_detector.domain.config import AppConfig
    from xray_detector.ui.detection_view import DetectionView

    monkeypatch.setattr(
        "xray_detector.ui.detection_view.list_devices",
        lambda: [DeviceInfo(0, "USB Video")],
    )
    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    view = DetectionView(config, settings)
    captured = []
    monkeypatch.setattr(
        view.camera_service,
        "set_source",
        lambda source_id, source: captured.append((source_id, source)) or None,
    )
    view.captured = captured
    return view


def test_selecting_file_restarts_both_files_with_same_start(view):
    view.left.restore_source("file", "C:/media/left.mp4")
    assert [source_id for source_id, _ in view.captured] == ["left"]

    view.right.restore_source("file", "C:/media/right.mp4")

    assert [source_id for source_id, _ in view.captured] == ["left", "right", "left"]
    right_source = view.captured[1][1]
    left_source = view.captured[2][1]
    assert right_source.path == Path("C:/media/right.mp4")
    assert left_source.path == Path("C:/media/left.mp4")
    assert right_source.start_at == left_source.start_at
    assert right_source.start_at > time.perf_counter()


def test_sync_works_in_both_directions(view):
    view.right.restore_source("file", "C:/media/right.mp4")
    view.captured.clear()

    view.left.restore_source("file", "C:/media/left.mp4")

    assert [source_id for source_id, _ in view.captured] == ["left", "right"]
    assert view.captured[0][1].start_at == view.captured[1][1].start_at


def test_selecting_file_leaves_uvc_source_alone(view, monkeypatch):
    import xray_detector.infrastructure.video.devices as devices

    monkeypatch.setattr(devices, "_windows_device_formats", lambda index: [])
    view.left.restore_source("uvc", 0)
    view.captured.clear()

    view.right.restore_source("file", "C:/media/right.mp4")

    assert [source_id for source_id, _ in view.captured] == ["right"]


def test_selecting_file_without_other_source_starts_only_one(view):
    view.right.restore_source("none", None)
    view.captured.clear()

    view.left.restore_source("file", "C:/media/left.mp4")

    assert [source_id for source_id, _ in view.captured] == ["left"]
