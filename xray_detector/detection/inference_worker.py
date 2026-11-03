"""InferenceWorker – QThread som kör detektering på nyaste frame per stream.

Mönster: capture-threads emitterar frames via signal → app kopplar dem till
push_frame() (queued connection, körs i inference-tråden). Worker-loopen tar
ALLTID nyaste frame per stream (drop-oldest) så att detektion aldrig hänger
efter, oavsett hur långsam inferensen är.
"""
from __future__ import annotations

import threading
import time

import numpy as np
from loguru import logger
from PySide6.QtCore import QThread, Signal

from xray_detector.detection.model_registry import BaseModel, Detection


class InferenceWorker(QThread):
    """Kör inferens på nyaste frame per stream.

    Signals:
        detections_ready(int, list): (stream_index, list[Detection])
        error(int, str): (stream_index, felmeddelande)
    """

    detections_ready = Signal(int, list)
    error = Signal(int, str)

    def __init__(
        self,
        models: dict[int, BaseModel],
        conf: float = 0.4,
        iou: float = 0.5,
        parent=None,
    ):
        super().__init__(parent)
        self.models = models  # {stream_index: BaseModel}
        self.conf = conf
        self.iou = iou
        self._latest: dict[int, np.ndarray] = {}
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._stop = False
        self._paused = False

    def push_frame(self, index: int, frame: np.ndarray) -> None:
        """Spara nyaste frame för en stream (kallas via signal, i worker-tråden)."""
        with self._cond:
            self._latest[index] = frame
            self._cond.notify_all()

    def set_paused(self, paused: bool) -> None:
        with self._cond:
            self._paused = paused
            self._cond.notify_all()

    def stop(self) -> None:
        with self._cond:
            self._stop = True
            self._cond.notify_all()
        self.wait(3000)

    def run(self) -> None:
        # Ladda alla modeller innan loopen (sakerställer att de är klara)
        for idx, model in self.models.items():
            try:
                model.load()
            except Exception as e:  # noqa: BLE001
                logger.exception("Kunde inte ladda modell för stream {}: {}", idx, e)
                self.error.emit(idx, f"Modellfel: {e}")

        logger.info("InferenceWorker startad ({} strömmar)", len(self.models))
        try:
            while not self._stop:
                if self._paused:
                    with self._cond:
                        self._cond.wait(timeout=0.2)
                    continue
                # Vänta på att minst ett frame ska vara tillgängligt
                with self._cond:
                    while not self._stop and not self._latest:
                        self._cond.wait(timeout=0.2)
                    if self._stop:
                        break
                    # Plocka ut och rensa de frames vi ska bearbeta nu
                    to_process = dict(self._latest)
                    self._latest.clear()

                # Kör inferens på varje stream (utanför låset)
                for idx, frame in to_process.items():
                    model = self.models.get(idx)
                    if model is None or frame is None:
                        continue
                    try:
                        dets = model.predict(frame, conf=self.conf, iou=self.iou)
                        self.detections_ready.emit(idx, dets)
                    except Exception as e:  # noqa: BLE001
                        logger.exception("Inferensfel stream {}: {}", idx, e)
                        self.error.emit(idx, str(e))
        finally:
            for model in self.models.values():
                model.close()
            logger.info("InferenceWorker stoppad")
