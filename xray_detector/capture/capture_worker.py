"""CaptureWorker – QThread som läser frames från en kamera i en loop."""
from __future__ import annotations

import time

import numpy as np
from loguru import logger
from PySide6.QtCore import QThread, Signal

from xray_detector.capture.camera import CameraSource
from xray_detector.config import StreamConfig
from xray_detector.detection.preprocess import preprocess


class CaptureWorker(QThread):
    """Läser frames från en kamera och emitterar dem via signal.

    Signals:
        frame_ready(int, np.ndarray): (stream_index, frame)
        error(int, str): (stream_index, felmeddelande)
    """

    frame_ready = Signal(int, object)
    error = Signal(int, str)

    def __init__(
        self,
        index: int,
        stream: StreamConfig,
        backend: str = "auto",
        preprocess_mode: str = "auto",
        parent=None,
    ):
        super().__init__(parent)
        self.index = index
        self.stream = stream
        self.backend = backend
        self.preprocess_mode = preprocess_mode
        self._camera = CameraSource(stream, backend)
        self._stop = False
        self._paused = False

    def run(self) -> None:
        if not self._camera.open_camera():
            self.error.emit(self.index, f"Kunde inte öppna kamera {self.index}")
            return

        frame_interval = 1.0 / max(1, self.stream.fps)
        logger.info("CaptureWorker {} startad", self.index)
        try:
            while not self._stop:
                if self._paused:
                    time.sleep(0.05)
                    continue
                ok, frame = self._camera.read()
                if not ok or frame is None:
                    # Försök återställa kameran
                    logger.warning("Tomt frame från kamera {}, återställer", self.index)
                    self._camera.close()
                    if not self._camera.open_camera():
                        self.error.emit(self.index, f"Kamera {self.index} förlorad")
                        return
                    continue
                frame = preprocess(frame, self.preprocess_mode)
                self.frame_ready.emit(self.index, frame)
                # Rate-limit till önskad FPS
                time.sleep(frame_interval)
        except Exception as e:  # noqa: BLE001
            logger.exception("CaptureWorker {} kraschade: {}", self.index, e)
            self.error.emit(self.index, str(e))
        finally:
            self._camera.close()
            logger.info("CaptureWorker {} stoppad", self.index)

    def stop(self) -> None:
        self._stop = True
        self.wait(2000)

    def set_paused(self, paused: bool) -> None:
        self._paused = paused
