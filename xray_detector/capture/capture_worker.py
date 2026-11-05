"""CaptureWorker – QThread som läser frames från en kamera i en loop."""
from __future__ import annotations

import time

from loguru import logger
from PySide6.QtCore import QThread, Signal

from xray_detector.capture.camera import CameraSource
from xray_detector.config import StreamConfig
from xray_detector.detection.preprocess import preprocess


class CaptureWorker(QThread):
    """Läser frames från en kamera och emitterar dem via signal.

    Vid en saknad eller tappad videokälla görs ett begränsat antal
    återanslutningsförsök. Därefter avslutas tråden och ett enda ``error``
    emitteras så att användaren kan försöka igen manuellt.

    Signals:
        frame_ready(int, np.ndarray): (stream_index, frame)
        connecting(int, int, int): (stream_index, försök, max_försök)
        error(int, str): (stream_index, felmeddelande)
    """

    frame_ready = Signal(int, object)
    connecting = Signal(int, int, int)
    error = Signal(int, str)

    # Antal anslutningsförsök innan videokällan anses saknad.
    MAX_ATTEMPTS = 3
    # Fördröjning mellan anslutningsförsöken (sekunder).
    RETRY_DELAY = 1.0

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
        self.max_attempts = max(1, self.MAX_ATTEMPTS)
        self.retry_delay = max(0.0, self.RETRY_DELAY)
        self._camera = CameraSource(stream, backend)
        self._stop = False
        self._paused = False

    def _wait_retry_delay(self) -> bool:
        """Vänta mellan återanslutningsförsök. Returnerar False vid stop."""
        deadline = time.monotonic() + self.retry_delay
        while not self._stop:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return True
            time.sleep(min(0.05, remaining))
        return False

    def _connect(self) -> bool:
        """Försök öppna kameran ett begränsat antal gånger."""
        for attempt in range(1, self.max_attempts + 1):
            if self._stop:
                return False
            self.connecting.emit(self.index, attempt, self.max_attempts)
            if self._camera.open_camera():
                if attempt == 1:
                    logger.info(
                        "CaptureWorker {} ansluten (kamera index={})",
                        self.index, self.stream.index,
                    )
                else:
                    logger.info(
                        "Kamera {} ansluten efter {} försök",
                        self.stream.index, attempt,
                    )
                return True
            if attempt < self.max_attempts:
                logger.debug(
                    "Kamera {} kunde inte öppnas (försök {}/{}), försöker igen",
                    self.stream.index, attempt, self.max_attempts,
                )
                if not self._wait_retry_delay():
                    return False

        logger.error(
            "Kunde inte öppna kamera {} efter {} försök",
            self.stream.index, self.max_attempts,
        )
        return False

    def run(self) -> None:
        if not self._connect():
            if not self._stop:
                self.error.emit(
                    self.index,
                    f"Kunde inte öppna kamera {self.stream.index}",
                )
            return

        frame_interval = 1.0 / max(1, self.stream.fps)
        failures = 0
        logger.info("CaptureWorker {} startad", self.index)
        try:
            while not self._stop:
                if self._paused:
                    time.sleep(0.05)
                    continue
                ok, frame = self._camera.read()
                if ok and frame is not None:
                    failures = 0
                    frame = preprocess(frame, self.preprocess_mode)
                    self.frame_ready.emit(self.index, frame)
                    # Rate-limit till önskad FPS
                    time.sleep(frame_interval)
                    continue

                # Tappad videokälla: försök återansluta ett begränsat antal
                # gånger i stället för att loopa och logga varje frame.
                failures += 1
                self._camera.close()
                if failures > self.max_attempts:
                    logger.error(
                        "Kamera {} förlorad efter {} återanslutningsförsök",
                        self.stream.index, self.max_attempts,
                    )
                    self.error.emit(
                        self.index,
                        f"Kamera {self.stream.index} förlorad",
                    )
                    return

                if failures == 1:
                    logger.warning(
                        "Ingen bild från kamera {} – försöker återansluta",
                        self.stream.index,
                    )
                else:
                    logger.debug(
                        "Kamera {} ger fortfarande ingen bild (försök {}/{})",
                        self.stream.index, failures, self.max_attempts,
                    )

                self.connecting.emit(self.index, failures, self.max_attempts)
                if not self._wait_retry_delay():
                    break
                self._camera.open_camera()
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
