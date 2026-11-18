"""Trådsäkerhet i detektionen (TASK-128)."""

import threading
import time

import numpy as np
import pytest

from xray_detector.domain.capture import StreamFrame
from xray_detector.domain.detection import Detection
from xray_detector.infrastructure.detectors.base import BaseDetector
from xray_detector.infrastructure.video.camera_service import StreamWorker
from xray_detector.infrastructure.video.source import SourceInfo, VideoSource


class OverlapDetector(BaseDetector):
    """Detektor som mäter hur många detect()-anrop som körs samtidigt."""

    def __init__(self) -> None:
        super().__init__(name="overlap", class_names=["kniv"])
        self.calls = 0
        self.active = 0
        self.max_active = 0
        self._guard = threading.Lock()

    def _detect(self, frame: np.ndarray) -> list[Detection]:
        with self._guard:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        time.sleep(0.01)
        with self._guard:
            self.active -= 1
            self.calls += 1
        return [Detection(1, 1, 5, 5, "kniv", 0.9)]


def _run_concurrently(detector, threads: int, calls: int) -> None:
    frame = np.zeros((16, 16, 3), dtype=np.uint8)

    def work() -> None:
        for _ in range(calls):
            detector.detect(frame)

    workers = [threading.Thread(target=work) for _ in range(threads)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=10)


def test_concurrent_detect_calls_are_serialised():
    """Två strömtrådar delar en detektor; anropen får inte överlappa (TASK-128)."""
    detector = OverlapDetector()

    _run_concurrently(detector, threads=2, calls=10)

    assert detector.calls == 20
    assert detector.max_active == 1, "detect() kördes parallellt på samma instans"


def test_settings_can_be_changed_while_detecting():
    """GUI-tråden får ändra tröskel och klasser medan trådarna detekterar (TASK-128)."""
    detector = OverlapDetector()
    stop = threading.Event()

    def change_settings() -> None:
        while not stop.is_set():
            detector.set_confidence_threshold(0.5)
            detector.set_enabled_classes(["kniv"])
            detector.set_enabled_classes(None)

    changer = threading.Thread(target=change_settings)
    changer.start()
    try:
        _run_concurrently(detector, threads=2, calls=10)
    finally:
        stop.set()
        changer.join(timeout=10)

    assert detector.calls == 20
    assert detector.max_active == 1


class EmptySource(VideoSource):
    """Källa som är slut direkt: read() ger None, som en fil som spelats klart."""

    def __init__(self) -> None:
        super().__init__(SourceInfo(label="tom"))
        self.reads = 0

    def _open(self):
        return _OpenCapture()

    def read(self):
        self.reads += 1
        return None


class _OpenCapture:
    """Minsta möjliga VideoCapture: isOpened() sant och release() utan verkan."""

    def isOpened(self) -> bool:
        return True

    def release(self) -> None:
        return None


def test_stream_worker_stops_after_the_source_ends(qapp):
    """source_lost signaleras en gång och loopen avslutas (TASK-128)."""
    source = EmptySource()
    worker = StreamWorker("left", source)
    lost: list[str] = []
    worker.source_lost.connect(lost.append)

    worker.start()
    assert worker.wait(5000), "arbetstråden avslutades inte"
    # signalen är köad till huvudtråden, som inte kör någon eventloop här
    qapp.processEvents()

    assert lost == ["left"], f"source_lost upprepades: {lost}"
    assert source.reads == 1


def test_stream_worker_stops_when_interrupted(qapp, video_file):
    """stop() avbryter loopen via requestInterruption (TASK-128)."""
    from xray_detector.infrastructure.video.source import FileSource

    worker = StreamWorker("left", FileSource(video_file))
    frames: list[StreamFrame] = []
    worker.frame_ready.connect(frames.append)
    worker.start()
    try:
        deadline = time.monotonic() + 5
        while not frames and time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.01)
        assert frames, "inga ramar kom"
    finally:
        worker.stop()

    # stop() avbryter loopen via requestInterruption och väntar ut tråden
    assert not worker.isRunning()


def test_qimage_owns_its_pixels(qapp):
    """_to_qimage lämnar en kopia som överlever anropet (TASK-128)."""
    from xray_detector.ui.stream_panel import StreamPanel

    frame = np.full((8, 8, 3), 200, dtype=np.uint8)
    image = StreamPanel._to_qimage(frame)
    frame[:] = 0

    assert image.pixelColor(0, 0).red() == 200


@pytest.mark.parametrize("threads", [2, 4])
def test_many_threads_never_overlap(threads):
    """Fler än två anropare serialiseras också (TASK-128)."""
    detector = OverlapDetector()

    _run_concurrently(detector, threads=threads, calls=5)

    assert detector.calls == threads * 5
    assert detector.max_active == 1
