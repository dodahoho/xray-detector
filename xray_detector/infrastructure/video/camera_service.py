import time

from PySide6.QtCore import QThread, Signal

from xray_detector.domain.capture import StreamFrame
from xray_detector.domain.detection import Detection
from xray_detector.infrastructure.detectors.base import BaseDetector
from xray_detector.infrastructure.detectors.smoothing import DetectionSmoother
from xray_detector.infrastructure.video.source import VideoSource

FPS_WINDOW_FRAMES = 30


class StreamWorker(QThread):
    frame_ready = Signal(object)
    source_lost = Signal(str)
    error_occurred = Signal(str, str)

    def __init__(self, source_id: str, source: VideoSource, parent=None) -> None:
        super().__init__(parent)
        self.source_id = source_id
        self.source = source
        self._detector: BaseDetector | None = None
        self._detections: list[Detection] = []
        self._smoother = DetectionSmoother()
        self._sequence = 0
        self._last_frame_time: float | None = None
        self._fps_window_start = time.perf_counter()
        self._fps_window_count = 0
        self._fps: float | None = None

    def set_detector(self, detector: BaseDetector | None) -> None:
        self._detector = detector
        # Overlayn visar föregående frames detektioner: utan detektor finns
        # ingen föregående detektion att visa (TASK-38).
        self._detections = []
        self._smoother.reset()
        # första ramen efter ett byte saknar tidsintervall att extrapolera med
        self._last_frame_time = None

    def _next_sequence(self) -> int:
        self._sequence += 1
        return self._sequence

    def _measure_fps(self) -> float | None:
        """Faktisk uppspelningshastighet, uppmätt över glidande 30 ramar."""
        self._fps_window_count += 1
        if self._fps_window_count >= FPS_WINDOW_FRAMES:
            elapsed = time.perf_counter() - self._fps_window_start
            if elapsed > 0:
                self._fps = self._fps_window_count / elapsed
            self._fps_window_start = time.perf_counter()
            self._fps_window_count = 0
        return self._fps

    def run(self) -> None:
        try:
            if self.isInterruptionRequested():
                return
            self.source.open()
            if not self.source.is_open():
                self.error_occurred.emit(
                    self.source_id, f"Kunde inte öppna {self.source.info.label}"
                )
                self.source_lost.emit(self.source_id)
                return
            detections: list[Detection]
            while not self.isInterruptionRequested():
                frame = self.source.read()
                if frame is None:
                    # Källan är slut eller borta: loopen avslutas i stället för
                    # att signalera source_lost var 500:e ms i evighet (TASK-128).
                    # Panelen begär en ny källa när den vill återansluta.
                    self._smoother.reset()
                    self._detections = []
                    self.source_lost.emit(self.source_id)
                    return
                # Ramen skickas direkt: detektionens varierande körtid får inte
                # förskjuta visningen (TASK-37). Overlayn visar därför senaste
                # ramens detektioner, alltså en ram efter bilden.
                # Tiden mellan två ramar är den tid rutan ska extrapoleras:
                # detektionen på den här ramen ritas på nästa (TASK-174).
                now = time.perf_counter()
                dt = 0.0 if self._last_frame_time is None else now - self._last_frame_time
                self._last_frame_time = now
                self.frame_ready.emit(
                    StreamFrame(
                        self.source_id,
                        frame,
                        self._detections,
                        self.source.info.label,
                        sequence=self._next_sequence(),
                        fps=self._measure_fps(),
                    )
                )
                detector = self._detector
                if detector is not None:
                    try:
                        detections = self._smoother.update(detector.detect(frame), dt)
                    except Exception as exc:
                        self.error_occurred.emit(self.source_id, str(exc))
                        self.msleep(500)
                        detections = []
                    # detektorn kan ha kopplats bort under körningen (TASK-38)
                    self._detections = detections if self._detector is detector else []
        finally:
            # Källan stängs i den tråd som öppnade den: DSHOW-fönstret ägs av
            # tråden, och release() från en annan tråd får drivrutinen att
            # logga "Failed to destroy the window" (TASK-27/28).
            self.source.close()

    def stop(self) -> None:
        self.requestInterruption()
        if not self.wait(5000):
            self.terminate()
            self.wait(2000)
        # no-op när arbetstråden redan stängt källan; fallback efter terminate()
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
