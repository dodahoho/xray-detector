from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from xray_detector.config import AppConfig
from xray_detector.dataset.pending import create_pending_capture
from xray_detector.detection.inference_worker import InferenceWorker
from xray_detector.detection.ultralytics_backend import (
    UltralyticsDetectorBackend,
    ultralytics_available,
)
from xray_detector.ui.video_panel import VideoPanel
from xray_detector.util.paths import AppPaths
from xray_detector.video.camera import CameraWorker

LOGGER = logging.getLogger(__name__)


class DetectionView(QWidget):
    captureReady = Signal(object)
    statusMessage = Signal(str)

    def __init__(self, config: AppConfig, paths: AppPaths, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.config = config
        self.paths = paths
        self.cameras: dict[str, CameraWorker] = {}
        self.inference: dict[str, InferenceWorker] = {}
        self._frame_ids: dict[str, int] = {"left": 0, "right": 0}
        self._detection_ids: dict[str, int] = {"left": 0, "right": 0}
        self._frame_counts: dict[str, int] = {"left": 0, "right": 0}
        self._detection_counts: dict[str, int] = {"left": 0, "right": 0}
        self._paused = False
        self._started = False

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        toolbar = QHBoxLayout()
        title = QLabel("Detektion")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        toolbar.addWidget(title)
        toolbar.addSpacing(16)
        self.model_label = QLabel("")
        toolbar.addWidget(self.model_label)
        toolbar.addSpacing(16)
        self.fps_label = QLabel("")
        toolbar.addWidget(self.fps_label)
        toolbar.addStretch(1)

        self.pause_label = QLabel("")
        self.pause_label.setStyleSheet("color: #ffb74d; font-weight: 600;")
        toolbar.addWidget(self.pause_label)
        self.capture_button = QPushButton("Fånga bildpar")
        self.capture_button.setMinimumHeight(38)
        self.capture_button.setMinimumWidth(160)
        self.capture_button.clicked.connect(self._capture)
        toolbar.addWidget(self.capture_button)
        root.addLayout(toolbar)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.panels = {
            "left": VideoPanel("Vänster kamera"),
            "right": VideoPanel("Höger kamera"),
        }
        for panel in self.panels.values():
            self.splitter.addWidget(panel)
        self.splitter.setSizes([1, 1])
        root.addWidget(self.splitter, 1)

        self._stats_timer = QTimer(self)
        self._stats_timer.setInterval(1000)
        self._stats_timer.timeout.connect(self._update_stats)
        self._stats_timer.start()

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        video = self.config.video
        detection = self.config.detection
        self.model_label.setText(f"Modell: {Path(detection.model).name}")

        can_detect = ultralytics_available()
        if not can_detect:
            self.statusMessage.emit(
                "Ultralytics är inte installerat – videovisning fungerar men detektion är avstängd."
            )
            self.pause_label.setText("Detektion ej tillgänglig")
        elif self._paused:
            self.pause_label.setText("Detektion pausad")

        for camera, index, name in (
            ("left", video.camera_left, "Vänster kamera"),
            ("right", video.camera_right, "Höger kamera"),
        ):
            camera_worker = CameraWorker(
                index=index,
                name=name,
                backend=video.backend,
                width=video.width,
                height=video.height,
                fps=video.fps,
                preview_fps=video.preview_fps,
            )
            camera_worker.frame.connect(lambda frame, key=camera: self._on_frame(key, frame))
            camera_worker.error.connect(lambda message, key=camera: self._on_camera_error(key, message))
            camera_worker.opened.connect(self.statusMessage.emit)
            self.cameras[camera] = camera_worker
            camera_worker.start()

            if can_detect:
                backend = UltralyticsDetectorBackend(detection.model, device=detection.device)
                worker = InferenceWorker(
                    backend,
                    name=name,
                    detection_fps=detection.detection_fps,
                    confidence=detection.confidence,
                    iou=detection.iou,
                    class_filter=detection.class_filter,
                )
                worker.result.connect(
                    lambda frame_id, detections, key=camera: self._on_detections(
                        key, frame_id, detections
                    )
                )
                worker.error.connect(lambda message, key=camera: self._on_camera_error(key, message))
                worker.ready.connect(self.statusMessage.emit)
                self.inference[camera] = worker
                worker.start()
        self._update_stats()

    def stop(self) -> None:
        for worker in self.cameras.values():
            worker.stop()
        for worker in self.inference.values():
            worker.stop()
        for worker in self.cameras.values():
            worker.wait(1500)
        for worker in self.inference.values():
            worker.wait(1500)
        self.cameras.clear()
        self.inference.clear()
        self._started = False

    def apply_config(self, config: AppConfig) -> None:
        self.stop()
        self.config = config
        for panel in self.panels.values():
            panel.clear()
        self._paused = False
        self.pause_label.setText("")
        self.start()

    def pause_inference(self, paused: bool) -> None:
        self._paused = paused
        for worker in self.inference.values():
            worker.set_paused(paused)
        if paused:
            self.pause_label.setText("Detektion pausad under träning")
        else:
            self.pause_label.setText("")
        self.statusMessage.emit(
            "Detektionen pausades för träning." if paused else "Detektionen är aktiv igen."
        )

    def _on_frame(self, camera: str, frame) -> None:  # type: ignore[no-untyped-def]
        self._frame_ids[camera] += 1
        self._frame_counts[camera] += 1
        self.panels[camera].set_frame(frame)
        worker = self.inference.get(camera)
        if worker is not None and not self._paused:
            worker.submit(self._frame_ids[camera], frame)

    def _on_detections(self, camera: str, frame_id: int, detections) -> None:  # type: ignore[no-untyped-def]
        self._detection_counts[camera] += 1
        if frame_id < self._detection_ids[camera]:
            return
        self._detection_ids[camera] = frame_id
        self.panels[camera].set_detections(detections)

    def _on_camera_error(self, camera: str, message: str) -> None:
        self.panels[camera].set_message(message)
        self.statusMessage.emit(message)
        LOGGER.warning("%s: %s", camera, message)

    def _capture(self) -> None:
        left = self.panels["left"].last_frame
        right = self.panels["right"].last_frame
        if left is None or right is None:
            QMessageBox.warning(
                self,
                "Fånga bildpar",
                "Båda kameraströmmarna måste visa bild innan ett bildpar kan fångas.",
            )
            return
        frames = {"left": left, "right": right}
        detections = {
            "left": self.panels["left"].detections,
            "right": self.panels["right"].detections,
        }
        try:
            capture = create_pending_capture(self.paths.pending, frames, detections)
        except Exception as exc:
            LOGGER.exception("Kunde inte fånga bildpar")
            QMessageBox.critical(self, "Fånga bildpar", f"Kunde inte spara bildparet: {exc}")
            return
        self.statusMessage.emit(f"Bildpar {capture.group_id} fångat.")
        self.captureReady.emit(capture)

    def _update_stats(self) -> None:
        if not self._started:
            return
        parts = []
        for camera, name in (("left", "V"), ("right", "H")):
            parts.append(
                f"{name}: {self._frame_counts[camera]} fps / {self._detection_counts[camera]} det/s"
            )
        self.fps_label.setText(" | ".join(parts))
        for camera in ("left", "right"):
            self._frame_counts[camera] = 0
            self._detection_counts[camera] = 0
