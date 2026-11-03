from __future__ import annotations

import logging
import sys
import threading
import time

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal

LOGGER = logging.getLogger(__name__)


def _api_preference(backend: str) -> int:
    if sys.platform != "win32":
        return getattr(cv2, "CAP_ANY", 0)
    if backend == "dshow":
        return getattr(cv2, "CAP_DSHOW", 0)
    if backend == "msmf":
        return getattr(cv2, "CAP_MSMF", 0)
    return getattr(cv2, "CAP_ANY", 0)


class CameraWorker(QThread):
    frame = Signal(object)
    opened = Signal(str)
    error = Signal(str)

    def __init__(
        self,
        index: int,
        name: str,
        backend: str = "dshow",
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        preview_fps: int = 30,
    ) -> None:
        super().__init__()
        self.index = index
        self.name = name
        self.backend = backend
        self.width = width
        self.height = height
        self.fps = fps
        self.preview_fps = max(1, preview_fps)
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()
        self.requestInterruption()

    def run(self) -> None:
        api = _api_preference(self.backend)
        capture = cv2.VideoCapture(self.index, api)
        if not capture.isOpened() and self.backend != "any" and sys.platform == "win32":
            capture.release()
            capture = cv2.VideoCapture(self.index, getattr(cv2, "CAP_ANY", 0))
        if not capture.isOpened():
            self.error.emit(
                f"Kunde inte oppna {self.name} (enhetsindex {self.index}). "
                "Kontrollera att kameran inte anvands av ett annat program."
            )
            capture.release()
            return

        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        capture.set(cv2.CAP_PROP_FPS, self.fps)
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        actual_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.opened.emit(f"{self.name}: {actual_width}x{actual_height}")

        interval = 1.0 / self.preview_fps
        next_frame = time.perf_counter()
        failures = 0
        try:
            while not self._stop.is_set() and not self.isInterruptionRequested():
                ok, frame = capture.read()
                if not ok or frame is None:
                    failures += 1
                    if failures >= 30:
                        self.error.emit(f"Videoflodet fran {self.name} avbröts.")
                        break
                    time.sleep(0.05)
                    continue
                failures = 0
                now = time.perf_counter()
                if now >= next_frame:
                    self.frame.emit(frame)
                    next_frame = now + interval
                else:
                    time.sleep(min(interval, max(0.0, next_frame - now)))
        except Exception as exc:  # pragma: no cover - handhavande av enhet
            LOGGER.exception("Kamerafel for %s", self.name)
            self.error.emit(f"Fel i {self.name}: {exc}")
        finally:
            capture.release()


def list_cameras(max_devices: int = 10, backend: str = "any") -> list[int]:
    available: list[int] = []
    api = _api_preference(backend)
    for index in range(max_devices):
        capture = cv2.VideoCapture(index, api)
        try:
            if capture.isOpened():
                ok, _ = capture.read()
                if ok:
                    available.append(index)
        finally:
            capture.release()
    return available
