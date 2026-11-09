"""Integrationstester mot demovideorna i media/ (UVC-simulering).

Testerna hoppar over automatiskt nar filmerna saknas sa sviten fungerar
aven pa maskiner utan binarerna; nar de finns verifieras riktig
 videotjandning: FileSource pacing, looping, StreamWorker med FakeDetector
samt GUI-panelens kallval av video fil.
"""

from pathlib import Path

import pytest

from xray_detector.infrastructure.video.source import FileSource

MEDIA_DIR = Path(__file__).parent.parent / "media"
SIDE = MEDIA_DIR / "xray_slideshow_side.mp4"
TOP = MEDIA_DIR / "xray_slideshow_top.mp4"

requires_media = pytest.mark.skipif(
    not (SIDE.exists() and TOP.exists()),
    reason="demovideorna i media/ finns inte pa denna maskin",
)


@requires_media
def test_sample_video_meta():
    import cv2

    for path in (SIDE, TOP):
        cap = cv2.VideoCapture(str(path))
        assert cap.isOpened(), path
        assert cap.get(cv2.CAP_PROP_FPS) == 30.0
        assert cap.get(cv2.CAP_PROP_FRAME_WIDTH) == 1280
        assert cap.get(cv2.CAP_PROP_FRAME_HEIGHT) == 720
        assert cap.get(cv2.CAP_PROP_FRAME_COUNT) == 2250
        cap.release()


@requires_media
def test_file_source_reads_real_xray_frames():
    source = FileSource(SIDE)
    source.open()
    try:
        first = source.read()
        assert first is not None
        assert first.shape == (720, 1280, 3)
        assert first.dtype == "uint8"
    finally:
        source.close()


@requires_media
def test_file_source_paces_to_30fps():
    import time

    source = FileSource(SIDE)
    source.open()
    try:
        source.read()  # starta intervallklockan
        start = time.perf_counter()
        for _ in range(10):
            source.read()
        elapsed = time.perf_counter() - start
    finally:
        source.close()
    # 10 ramar vid 30 fps = ca 0,33 s; tillat lite slack for kompilering
    assert 0.2 <= elapsed <= 0.6, elapsed


@requires_media
def test_stream_worker_with_real_video(qapp, fake_detector):
    from xray_detector.infrastructure.video.camera_service import StreamWorker
    from tests.test_stream_worker import wait_for

    worker = StreamWorker("left", FileSource(SIDE))
    received = []
    worker.frame_ready.connect(lambda frame: received.append(frame))
    worker.error_occurred.connect(lambda _, msg: pytest.fail(msg))
    worker.set_detector(fake_detector)
    worker.start()
    try:
        assert wait_for(qapp, lambda: len(received) >= 3), "inga ramar togs emot"
    finally:
        worker.stop()
    frame = received[0]
    assert frame.frame.shape == (720, 1280, 3)
    assert frame.detections, "FakeDetector gav inga detektioner pa riktig video"
    assert frame.sequence >= 1


@requires_media
def test_gui_panel_selects_sample_video(qapp, monkeypatch):
    from PySide6.QtWidgets import QFileDialog

    from xray_detector.ui.detection_view import StreamPanel

    paths = {"call": 0}

    def fake_dialog(parent, caption, directory, filters):
        paths["call"] += 1
        return str(TOP), ""

    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(fake_dialog))
    panel = StreamPanel("left", "Strom 1")
    emitted = []
    panel.source_requested.connect(lambda sid, kind, value: emitted.append((kind, value)))
    index = panel.source_combo.findData("file")
    panel.source_combo.setCurrentIndex(index)
    assert emitted == [("file", Path(TOP))], emitted
    assert panel.source_combo.currentText() == "xray_slideshow_top.mp4"
    assert panel.current_source() == ("file", str(TOP))
