from PySide6.QtCore import QThread, Signal

from xray_detector.domain.capture import StreamFrame
from xray_detector.infrastructure.detectors.base import BaseDetector
from xray_detector.infrastructure.video.source import VideoSource


class StreamWorker(QThread):
    frame_ready = Signal(object)
    source_lost = Signal(str)
    error_occurred = Signal(str, str)

    def __init__(self, source_id: str, source: VideoSource, parent=None) -> None:
        super().__init__(parent)
        self.source_id = source_id
        self.source = source
        self._detector: BaseDetector | None = None
        self._running = False

    def set_detector(self, detector: BaseDetector | None) -> None:
        self._detector = detector

    def run(self) -> None:
        self._running = True
        self.source.open()
        if not self.source.is_open():
            self.error_occurred.emit(
                self.source_id, f"Kunde inte öppna {self.source.info.label}"
            )
            self.source_lost.emit(self.source_id)
            return
        while self._running:
            frame = self.source.read()
            if frame is None:
                self.source_lost.emit(self.source_id)
                self.msleep(500)
                continue
            detections = []
            if self._detector is not None:
                try:
                    detections = self._detector.detect(frame)
                except Exception as exc:
                    self.error_occurred.emit(self.source_id, str(exc))
                    self.msleep(500)
                    continue
            self.frame_ready.emit(
                StreamFrame(self.source_id, frame, detections, self.source.info.label)
            )

    def stop(self) -> None:
        self._running = False
        if not self.wait(5000):
            self.terminate()
            self.wait(2000)
        self.source.close()


class CameraService:
    def __init__(self) -> None:
        self._workers: dict[str, StreamWorker] = {}

    def set_source(self, source_id: str, source: VideoSource | None) -> StreamWorker | None:
        self.stop_source(source_id)
        if source is None:
            return None
        worker = StreamWorker(source_id, source)
        self._workers[source_id] = worker
        worker.start()
        return worker

    def set_detector(self, detector: BaseDetector | None) -> None:
        for worker in self._workers.values():
            worker.set_detector(detector)

    def worker(self, source_id: str) -> StreamWorker | None:
        return self._workers.get(source_id)

    def stop_source(self, source_id: str) -> None:
        worker = self._workers.pop(source_id, None)
        if worker is not None:
            worker.stop()

    def stop_all(self) -> None:
        for source_id in list(self._workers):
            self.stop_source(source_id)
