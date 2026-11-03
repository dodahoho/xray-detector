"""Qt worker threads for capture and inference."""

from __future__ import annotations

import contextlib
import logging
import threading
import time
import uuid
from datetime import UTC, datetime

from PySide6.QtCore import QObject, QThread, Signal

from xray_detector.config import AppConfig
from xray_detector.domain.detection import CaptureSnapshot, Detection, FramePacket
from xray_detector.infrastructure.detectors.base import Detector
from xray_detector.infrastructure.video.frame_buffer import FrameBuffer
from xray_detector.infrastructure.video.source import SourceSpec, create_source

logger = logging.getLogger(__name__)


class CaptureWorker(QThread):
    frame_ready = Signal(str, object)
    status_changed = Signal(str, str)
    failed = Signal(str, str)

    def __init__(
        self,
        role: str,
        spec: SourceSpec,
        buffer: FrameBuffer,
        preview_fps: int = 30,
    ) -> None:
        super().__init__()
        self.role = role
        self.spec = spec
        self.buffer = buffer
        self.preview_fps = max(1, preview_fps)
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        backoff = 1.0
        while not self._stop_event.is_set():
            source = None
            try:
                source = create_source(self.spec)
                source.open()
                self.status_changed.emit(self.role, f"Öppnad: {source.description}")
                backoff = 1.0
                last_preview = 0.0
                frame_interval = 1.0 / max(1, self.spec.fps)
                while not self._stop_event.is_set():
                    loop_start = time.monotonic()
                    frame = source.read()
                    if frame is None:
                        if source.at_end:
                            self.status_changed.emit(self.role, "Källan har nått slutet")
                            if self.spec.type == "file" and not self.spec.loop_file:
                                self._stop_event.wait()
                            break
                        raise RuntimeError("Kunde inte läsa frame")
                    now = time.monotonic()
                    packet = self.buffer.update(frame, time.time())
                    if now - last_preview >= 1.0 / self.preview_fps:
                        last_preview = now
                        self.frame_ready.emit(self.role, packet)
                    if self.spec.type in ("test_pattern", "file"):
                        remaining = frame_interval - (time.monotonic() - loop_start)
                        if remaining > 0:
                            time.sleep(remaining)
                if self.spec.type != "file" and not self._stop_event.is_set():
                    time.sleep(backoff)
            except Exception as exc:
                logger.exception("Capture worker %s failed", self.role)
                self.failed.emit(self.role, f"{self.spec.description}: {exc}")
                self.status_changed.emit(self.role, f"Fel: {exc}")
                if self._stop_event.wait(backoff):
                    break
                backoff = min(backoff * 1.5, 5.0)
            finally:
                if source is not None:
                    source.close()

    def run_once(self) -> FramePacket | None:
        """Synchronous helper used by tests."""
        source = create_source(self.spec)
        source.open()
        try:
            frame = source.read()
            if frame is None:
                return None
            return self.buffer.update(frame, time.time())
        finally:
            source.close()


class InferenceWorker(QThread):
    detections_ready = Signal(str, int, object)
    status_changed = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        buffers: dict[str, FrameBuffer],
        detector: Detector,
        max_fps: int = 30,
    ) -> None:
        super().__init__()
        self.buffers = buffers
        self.detector = detector
        self.max_fps = max(1, max_fps)
        self._stop_event = threading.Event()
        self._active = threading.Event()
        self._active.set()
        self._lock = threading.Lock()
        self._latest: dict[str, tuple[int, list[Detection]]] = {}

    def stop(self) -> None:
        self._stop_event.set()

    def set_active(self, active: bool) -> None:
        if active:
            self._active.set()
        else:
            self._active.clear()

    def latest_detections(self) -> dict[str, tuple[int, list[Detection]]]:
        with self._lock:
            return dict(self._latest)

    def run(self) -> None:
        try:
            self.status_changed.emit(f"Laddar modell {self.detector.metadata.display_name}...")
            self.detector.load()
            self.status_changed.emit(f"Modell redo: {self.detector.metadata.display_name}")
        except Exception as exc:
            logger.exception("Detector loading failed")
            self.failed.emit(str(exc))
            return

        last_sequences: dict[str, int] = {role: 0 for role in self.buffers}
        min_interval = 1.0 / self.max_fps
        last_cycle = 0.0
        while not self._stop_event.is_set():
            if not self._active.is_set():
                self._stop_event.wait(0.05)
                continue
            now = time.monotonic()
            if now - last_cycle < min_interval:
                self._stop_event.wait(max(0.0, min_interval - (now - last_cycle)))
                continue
            last_cycle = time.monotonic()
            processed = False
            for role, buffer in self.buffers.items():
                packet = buffer.latest()
                if packet is None or packet.sequence == last_sequences.get(role, 0):
                    continue
                processed = True
                last_sequences[role] = packet.sequence
                try:
                    detections = self.detector.predict(packet.frame)
                except Exception as exc:
                    logger.exception("Inference failed for %s", role)
                    self.failed.emit(str(exc))
                    self._stop_event.wait(1.0)
                    continue
                with self._lock:
                    self._latest[role] = (packet.sequence, detections)
                self.detections_ready.emit(role, packet.sequence, detections)
            if not processed:
                self._stop_event.wait(0.005)

        with contextlib.suppress(Exception):
            self.detector.close()


class DetectionPipeline(QObject):
    frame_ready = Signal(str, object)
    detections_ready = Signal(str, int, object)
    status_changed = Signal(str, str)
    failed = Signal(str, str)

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.config = config
        self._capture_workers: list[CaptureWorker] = []
        self._inference_worker: InferenceWorker | None = None
        self._buffers: dict[str, FrameBuffer] = {}
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def start(
        self,
        specs: dict[str, SourceSpec],
        detector: Detector,
        preview_fps: int = 30,
    ) -> None:
        self.stop()
        self._buffers = {role: FrameBuffer(role) for role in specs}
        self._capture_workers = []
        for role, spec in specs.items():
            worker = CaptureWorker(role, spec, self._buffers[role], preview_fps)
            worker.frame_ready.connect(self.frame_ready)
            worker.status_changed.connect(self.status_changed)
            worker.failed.connect(self.failed)
            self._capture_workers.append(worker)

        self._inference_worker = InferenceWorker(
            self._buffers, detector, self.config.detection.max_fps
        )
        self._inference_worker.detections_ready.connect(self.detections_ready)
        self._inference_worker.status_changed.connect(
            lambda message: self.status_changed.emit("model", message)
        )
        self._inference_worker.failed.connect(lambda message: self.failed.emit("model", message))

        for worker in self._capture_workers:
            worker.start()
        self._inference_worker.start()
        self._running = True
        logger.info("Detection pipeline started with %d sources", len(specs))

    def stop(self) -> None:
        self._running = False
        if self._inference_worker is not None:
            self._inference_worker.stop()
            self._inference_worker.wait(3000)
            self._inference_worker = None
        for worker in self._capture_workers:
            worker.stop()
        for worker in self._capture_workers:
            worker.wait(3000)
        self._capture_workers = []
        self._buffers = {}

    def set_active(self, active: bool) -> None:
        if self._inference_worker is not None:
            self._inference_worker.set_active(active)

    def capture(self) -> CaptureSnapshot:
        if not self._running:
            raise RuntimeError("Detektionen är inte igång")
        frames: dict[str, object] = {}
        sequences: dict[str, int] = {}
        for role, buffer in self._buffers.items():
            packet = buffer.snapshot()
            if packet is None:
                raise RuntimeError(f"Ingen bildruta från {role}")
            frames[role] = packet.frame
            sequences[role] = packet.sequence

        detections: dict[str, list[Detection]] = {role: [] for role in self._buffers}
        if self._inference_worker is not None:
            latest = self._inference_worker.latest_detections()
            for role in self._buffers:
                if role in latest:
                    detections[role] = list(latest[role][1])

        return CaptureSnapshot(
            frames=frames,  # type: ignore[arg-type]
            detections=detections,
            sequences=sequences,
            captured_at=datetime.now(UTC).replace(microsecond=0).isoformat(),
            pair_id=uuid.uuid4().hex[:12],
        )
