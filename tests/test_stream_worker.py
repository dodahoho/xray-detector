"""StreamWorker-tester: videofil + FakeDetector i QThread, helt utan kamera."""

import cv2
import numpy as np
import pytest
from PySide6.QtCore import QTimer

from tests.conftest import synthetic_frame
from xray_detector.infrastructure.video.camera_service import FPS_WINDOW_FRAMES, StreamWorker
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


def test_stream_worker_numbers_frames_monotonically(qapp, video_file, fake_detector):
    worker = StreamWorker("left", FileSource(video_file))
    received = []
    worker.frame_ready.connect(lambda frame: received.append(frame))
    worker.set_detector(fake_detector)
    worker.start()
    try:
        assert wait_for(qapp, lambda: len(received) >= 3), "inga ramer togs emot"
    finally:
        worker.stop()
    sequences = [frame.sequence for frame in received]
    assert sequences == sorted(sequences) and len(set(sequences)) == len(sequences)
    assert sequences[0] >= 1


def test_stream_worker_measures_fps(qapp, video_file):
    worker = StreamWorker("left", FileSource(video_file))
    received = []
    worker.frame_ready.connect(lambda frame: received.append(frame))
    worker.start()
    try:
        assert wait_for(qapp, lambda: len(received) >= FPS_WINDOW_FRAMES), "for fa ramar for fps-matning"
    finally:
        worker.stop()
    fps_values = [frame.fps for frame in received if frame.fps]
    assert fps_values and all(value > 0 for value in fps_values)


def test_stream_frame_defaults_backward_compatible():
    from xray_detector.domain.capture import StreamFrame as SF
    import numpy as np

    frame = SF(source_id="x", frame=np.zeros((4, 4, 3), np.uint8), detections=[], source_label="l")
    assert frame.sequence == 0
    assert frame.fps is None


def test_panel_title_shows_fps(qapp):
    from PySide6.QtCore import Signal
    from xray_detector.ui.detection_view import StreamPanel
    from xray_detector.domain.capture import StreamFrame
    from tests.conftest import synthetic_frame

    panel = StreamPanel("left", "Ström 1")
    panel._show_no_source()
    assert panel.title_label.text() == "Ström 1"
    panel.show_frame(StreamFrame("left", synthetic_frame(), [], "k", sequence=1, fps=29.321))
    assert "29.3 fps" in panel.title_label.text()


class _ThreadRecordingSource(FileSource):
    """FileSource som minns vilken tråd som öppnade respektive stängde den."""

    def __init__(self, path):
        super().__init__(path)
        self.open_thread = None
        self.close_thread = None

    def open(self):
        if self._capture is None:
            import threading

            self.open_thread = threading.get_ident()
        super().open()

    def close(self):
        if self._capture is not None:
            import threading

            self.close_thread = threading.get_ident()
        super().close()


def test_worker_closes_source_in_its_own_thread(qapp, video_file):
    """release() ska ske i arbetstråden, inte i GUI-tråden (TASK-27)."""
    import threading

    source = _ThreadRecordingSource(video_file)
    worker = StreamWorker("left", source)
    received = []
    worker.frame_ready.connect(lambda frame: received.append(frame))
    worker.start()
    try:
        assert wait_for(qapp, lambda: len(received) >= 1), "inga ramer togs emot"
    finally:
        worker.stop()

    assert source.open_thread is not None
    assert source.close_thread == source.open_thread
    assert source.close_thread != threading.get_ident()


def test_stop_right_after_start_finishes_quickly(qapp, video_file):
    """stop() direkt efter start() får inte fastna i en loop som termineras."""
    import time

    worker = StreamWorker("left", FileSource(video_file))
    worker.start()
    started = time.perf_counter()
    worker.stop()
    elapsed = time.perf_counter() - started

    assert worker.isFinished()
    assert elapsed < 2.0, "stop() tvingades vanta ut en trad som aldrig avslutades"


def test_camera_service_switch_closes_old_source_in_worker_thread(qapp, video_file):
    """Byte av källa stänger gamla källan i dess tråd innan nästa öppnas (TASK-28)."""
    import threading

    from xray_detector.infrastructure.video.camera_service import CameraService

    service = CameraService()
    first = _ThreadRecordingSource(video_file)
    service.set_source("left", first)
    assert wait_for(qapp, lambda: first.open_thread is not None), "forsta kallan oppnades inte"

    second = _ThreadRecordingSource(video_file)
    service.set_source("left", second)
    try:
        assert first.close_thread == first.open_thread
        assert first.close_thread != threading.get_ident()
        assert wait_for(qapp, lambda: second.open_thread is not None)
    finally:
        service.stop_all()

    assert second.close_thread == second.open_thread
    assert service.worker("left") is None
