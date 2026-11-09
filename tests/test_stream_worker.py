"""StreamWorker-tester: videofil + FakeDetector i QThread, helt utan kamera."""

import cv2
import numpy as np
import pytest
from PySide6.QtCore import QTimer

from tests.conftest import synthetic_frame
from xray_detector.infrastructure.video.camera_service import StreamWorker
from xray_detector.infrastructure.video.source import FileSource


@pytest.fixture
def video_file(tmp_path):
    path = tmp_path / "stream.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 60, (64, 48))
    assert writer.isOpened(), "mp4v-codec saknas i denna OpenCV-byggnad"
    for i in range(12):
        frame = synthetic_frame(fill=100 + i)
        writer.write(frame)
    writer.release()
    return path


def wait_for(qapp, predicate, timeout_ms=8000, step_ms=25):
    elapsed = 0
    while elapsed < timeout_ms:
        qapp.processEvents()
        if predicate():
            return True
        QTimer.singleShot(step_ms, lambda: None)
        import time

        time.sleep(step_ms / 1000)
        elapsed += step_ms
    return False


def test_file_source_reads_all_frames(video_file):
    source = FileSource(video_file)
    source.open()
    frames = 0
    while source.read() is not None and frames < 50:
        frames += 1
    source.close()
    assert frames >= 12


def test_stream_worker_emits_frames_with_detections(qapp, video_file, fake_detector):
    worker = StreamWorker("left", FileSource(video_file))
    received = []
    worker.frame_ready.connect(lambda frame: received.append(frame))
    worker.error_occurred.connect(lambda _, msg: pytest.fail(msg))
    worker.set_detector(fake_detector)
    worker.start()

    try:
        assert wait_for(qapp, lambda: len(received) >= 2), "inga ramer togs emot"
    finally:
        worker.stop()

    frame = received[0]
    assert frame.source_id == "left"
    assert frame.frame.shape == (48, 64, 3)
    assert frame.detections, "FakeDetector gav inga detektioner"
    assert frame.detections[0].class_name == "kniv"


def test_stream_worker_without_detector_emits_empty_detections(qapp, video_file):
    worker = StreamWorker("right", FileSource(video_file))
    received = []
    worker.frame_ready.connect(lambda frame: received.append(frame))
    worker.start()
    try:
        assert wait_for(qapp, lambda: len(received) >= 1), "inga ramer togs emot"
    finally:
        worker.stop()
    assert received[0].detections == []
    assert np.asarray(received[0].frame).dtype == np.uint8
