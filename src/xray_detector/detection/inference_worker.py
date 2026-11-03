from __future__ import annotations

import logging
import threading
import time
from typing import Sequence

import numpy as np
from PySide6.QtCore import QThread, Signal

from xray_detector.detection.backend import DetectorBackend, DetectorError

LOGGER = logging.getLogger(__name__)


class InferenceWorker(QThread):
    result = Signal(int, object)
    error = Signal(str)
    ready = Signal(str)

    def __init__(
        self,
        backend: DetectorBackend,
        name: str,
        detection_fps: float = 10.0,
        confidence: float = 0.25,
        iou: float = 0.45,
        class_filter: Sequence[int] | None = None,
    ) -> None:
        super().__init__()
        self.backend = backend
        self.name = name
        self.detection_fps = max(0.1, detection_fps)
        self.confidence = confidence
        self.iou = iou
        self.class_filter = list(class_filter) if class_filter else None
        self._lock = threading.Lock()
        self._latest: tuple[int, np.ndarray] | None = None
        self._paused = threading.Event()
        self._stop = threading.Event()

    def submit(self, frame_id: int, frame: np.ndarray) -> None:
        with self._lock:
            self._latest = (frame_id, frame)

    def set_paused(self, paused: bool) -> None:
        if paused:
            self._paused.set()
        else:
            self._paused.clear()

    def stop(self) -> None:
        self._stop.set()
        self.requestInterruption()

    def run(self) -> None:
        try:
            self.backend.load()
        except DetectorError as exc:
            self.error.emit(str(exc))
            return
        except Exception as exc:
            LOGGER.exception("Ovatntat modellfel")
            self.error.emit(f"Kunde inte ladda modellen: {exc}")
            return

        self.ready.emit(f"{self.name}: modell redo")
        interval = 1.0 / self.detection_fps
        next_allowed = 0.0
        while not self._stop.is_set() and not self.isInterruptionRequested():
            if self._paused.is_set():
                time.sleep(0.05)
                continue
            with self._lock:
                item = self._latest
                self._latest = None
            if item is None:
                time.sleep(0.01)
                continue
            now = time.perf_counter()
            if now < next_allowed:
                time.sleep(min(interval, next_allowed - now))
                continue
            frame_id, frame = item
            try:
                detections = self.backend.detect(
                    frame,
                    confidence=self.confidence,
                    iou=self.iou,
                    class_filter=self.class_filter,
                )
            except DetectorError as exc:
                self.error.emit(str(exc))
                time.sleep(0.5)
                continue
            except Exception as exc:  # pragma: no cover - skydd mot backendfel
                LOGGER.exception("Ovatntat detektionsfel")
                self.error.emit(f"Detektionsfel: {exc}")
                time.sleep(0.5)
                continue
            self.result.emit(frame_id, detections)
            next_allowed = time.perf_counter() + interval
