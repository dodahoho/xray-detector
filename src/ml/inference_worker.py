from __future__ import annotations

import threading
import time
from typing import Optional
from PySide6.QtCore import QThread, Signal

from src.core.models_schema import StreamFrameResult
from src.ml.base import BaseDetector
from src.ml.model_registry import ModelRegistry
from src.video.stream_manager import StreamManager


class InferenceWorker(QThread):
    """Kör objektdetektion på båda videoströmmarna i en egen bakgrundstråd utan att blockera GUI.

    Kan pausas under modellträning för att frigöra GPU/CPU-resurser.
    """

    frames_processed = Signal(object, object)  # (StreamFrameResult 1, StreamFrameResult 2)
    status_changed = Signal(str)

    def __init__(
        self,
        stream_manager: StreamManager,
        model_family: str = "YOLO26",
        weights_path: str = "yolo26n.pt",
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        target_fps: int = 30,
    ) -> None:
        super().__init__()
        self.stream_manager = stream_manager
        self.target_fps = max(1, target_fps)

        self._lock = threading.Lock()
        self._running = False
        self._paused = False
        self._detector: BaseDetector = ModelRegistry.create_detector(
            model_family=model_family,
            weights_path=weights_path,
            confidence_threshold=confidence_threshold,
            iou_threshold=iou_threshold,
        )
        self._pending_detector: Optional[BaseDetector] = None

    def switch_model(
        self,
        model_family: str,
        weights_path: str,
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.45,
    ) -> None:
        """Byter aktiv detektionsmodell trådsäkert under körning."""
        new_det = ModelRegistry.create_detector(
            model_family=model_family,
            weights_path=weights_path,
            confidence_threshold=confidence_threshold,
            iou_threshold=iou_threshold,
        )
        with self._lock:
            self._pending_detector = new_det

    def set_confidence_threshold(self, conf: float) -> None:
        with self._lock:
            self._detector.confidence_threshold = conf

    def set_paused(self, paused: bool) -> None:
        """Pausar eller återupptar detektion (och frigör modellresurser vid paus för maximal träningsprestanda)."""
        with self._lock:
            if self._paused == paused:
                return
            self._paused = paused
            if paused:
                self._detector.unload()
                self.status_changed.emit("Detektion pausad (frigör hårdvaruresurser för träning)")
            else:
                self._detector.load()
                self.status_changed.emit(f"Detektion aktiv ({self._detector.model_family})")

    def is_paused(self) -> bool:
        with self._lock:
            return self._paused

    def stop(self) -> None:
        self._running = False
        self.wait(2000)

    def run(self) -> None:
        self._running = True
        with self._lock:
            self._detector.load()
            self.status_changed.emit(f"Detektion aktiv ({self._detector.model_family})")

        interval = 1.0 / float(self.target_fps)

        while self._running:
            t0 = time.perf_counter()

            with self._lock:
                if self._pending_detector is not None:
                    self._detector.unload()
                    self._detector = self._pending_detector
                    self._pending_detector = None
                    if not self._paused:
                        self._detector.load()
                    self.status_changed.emit(f"Modell bytt till {self._detector.model_family}")

                is_paused = self._paused
                active_detector = self._detector

            if is_paused:
                time.sleep(0.1)
                continue

            (frame1, fps1), (frame2, fps2) = self.stream_manager.get_latest_frames()

            res1: Optional[StreamFrameResult] = None
            res2: Optional[StreamFrameResult] = None

            if frame1 is not None:
                boxes1 = active_detector.predict(frame1)
                res1 = StreamFrameResult(
                    stream_id=1,
                    stream_name=self.stream_manager.worker_1.stream_name,
                    frame_bgr=frame1,
                    detections=boxes1,
                    fps=fps1,
                )

            if frame2 is not None:
                boxes2 = active_detector.predict(frame2)
                res2 = StreamFrameResult(
                    stream_id=2,
                    stream_name=self.stream_manager.worker_2.stream_name,
                    frame_bgr=frame2,
                    detections=boxes2,
                    fps=fps2,
                )

            if res1 is not None and res2 is not None:
                self.frames_processed.emit(res1, res2)

            elapsed = time.perf_counter() - t0
            sleep_time = interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        with self._lock:
            self._detector.unload()
