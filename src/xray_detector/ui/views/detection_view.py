"""Detection mode view."""

from __future__ import annotations

import logging

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from xray_detector.application.model_registry import ModelRegistry
from xray_detector.config import AppConfig
from xray_detector.domain.detection import CaptureSnapshot
from xray_detector.infrastructure.detectors.registry import create_detector
from xray_detector.infrastructure.video.source import SourceSpec
from xray_detector.ui.pipeline import DetectionPipeline
from xray_detector.ui.widgets.video_panel import VideoPanel

logger = logging.getLogger(__name__)


class DetectionView(QWidget):
    capture_requested = Signal(object)

    def __init__(
        self,
        config: AppConfig,
        model_registry: ModelRegistry,
        pipeline: DetectionPipeline,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.config = config
        self.model_registry = model_registry
        self.pipeline = pipeline
        self._loading_models = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Modell:"))
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(260)
        toolbar.addWidget(self.model_combo)
        toolbar.addStretch(1)

        self.status_label = QLabel("Redo")
        self.status_label.setStyleSheet("color: #a8a8b8;")
        toolbar.addWidget(self.status_label)

        self.start_button = QPushButton("Starta")
        self.start_button.clicked.connect(self.toggle_detection)
        toolbar.addWidget(self.start_button)

        self.capture_button = QPushButton("Fånga bildpar")
        self.capture_button.setMinimumHeight(38)
        self.capture_button.setStyleSheet(
            "QPushButton { background-color: #2f7d5b; color: white; font-weight: bold; "
            "padding: 6px 18px; border-radius: 4px; } "
            "QPushButton:hover { background-color: #38956c; }"
        )
        self.capture_button.clicked.connect(self._capture)
        self.capture_button.setEnabled(False)
        toolbar.addWidget(self.capture_button)
        layout.addLayout(toolbar)

        splitter = QSplitter()
        self.panel0 = VideoPanel("Kamera 0 / cam0")
        self.panel1 = VideoPanel("Kamera 1 / cam1")
        splitter.addWidget(self.panel0)
        splitter.addWidget(self.panel1)
        splitter.setSizes([640, 640])
        layout.addWidget(splitter, 1)

        hint = QLabel(
            "Fånga skapar ett bildpar från båda strömmarna och öppnar annoteringsläget. "
            "F11 växlar fullscreen."
        )
        hint.setStyleSheet("color: #858595;")
        layout.addWidget(hint)

        self.pipeline.frame_ready.connect(self._on_frame)
        self.pipeline.detections_ready.connect(self._on_detections)
        self.pipeline.status_changed.connect(self._on_status)
        self.pipeline.failed.connect(self._on_failed)
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)
        self.populate_models()

    def populate_models(self, selected_id: str | None = None) -> None:
        self._loading_models = True
        try:
            current = selected_id or self.model_combo.currentData()
            self.model_combo.clear()
            for model in self.model_registry.list_models():
                label = model.display_name
                if model.trained:
                    label = f"{label} [tränad]"
                self.model_combo.addItem(label, model.id)
            if current:
                index = self.model_combo.findData(current)
            else:
                index = self.model_combo.findData(self.config.app.default_model)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
        finally:
            self._loading_models = False

    def current_model_id(self) -> str | None:
        return self.model_combo.currentData()

    def toggle_detection(self) -> None:
        if self.pipeline.is_running:
            self.stop_detection()
        else:
            self.start_detection()

    def start_detection(self) -> None:
        if self.pipeline.is_running:
            return
        model_id = self.current_model_id()
        if not model_id:
            QMessageBox.warning(self, "Ingen modell", "Ingen detektionsmodell är vald.")
            return
        try:
            metadata = self.model_registry.get(model_id)
            detector = create_detector(metadata, self.config.detection)
        except Exception as exc:
            QMessageBox.critical(self, "Modellfel", str(exc))
            return

        specs = {
            "cam0": SourceSpec.from_settings("cam0", self.config.video.cam0),
            "cam1": SourceSpec.from_settings("cam1", self.config.video.cam1),
        }
        self.panel0.clear()
        self.panel1.clear()
        self.pipeline.start(specs, detector)
        self.start_button.setText("Stoppa")
        self.status_label.setText("Startar...")
        self.capture_button.setEnabled(True)
        self.config.app.default_model = model_id

    def stop_detection(self) -> None:
        if self.pipeline.is_running:
            self.pipeline.stop()
        self.start_button.setText("Starta")
        self.status_label.setText("Stoppad")
        self.capture_button.setEnabled(False)
        self.panel0.clear()
        self.panel1.clear()

    def _on_frame(self, role: str, packet) -> None:
        panel = self.panel0 if role == "cam0" else self.panel1
        panel.set_frame(packet)

    def _on_detections(self, role: str, sequence: int, detections) -> None:
        panel = self.panel0 if role == "cam0" else self.panel1
        panel.set_detections(sequence, detections)

    def _on_status(self, role: str, message: str) -> None:
        if role == "cam0":
            self.panel0.set_status(message)
            self.status_label.setText(f"cam0: {message}")
        elif role == "cam1":
            self.panel1.set_status(message)
            self.status_label.setText(f"cam1: {message}")
        else:
            self.status_label.setText(message)

    def _on_failed(self, role: str, message: str) -> None:
        logger.error("Pipeline failure (%s): %s", role, message)
        self.status_label.setText(f"Fel ({role}): {message}")
        panel = self.panel0 if role == "cam0" else self.panel1
        panel.set_status(f"Fel: {message}")

    def _on_model_changed(self, index: int) -> None:
        if self._loading_models or index < 0:
            return
        model_id = self.model_combo.currentData()
        if model_id:
            self.config.app.default_model = model_id
        if self.pipeline.is_running:
            self.stop_detection()
            self.start_detection()

    def _capture(self) -> None:
        try:
            snapshot: CaptureSnapshot = self.pipeline.capture()
        except Exception as exc:
            QMessageBox.warning(self, "Kunde inte fånga", str(exc))
            return
        self.capture_requested.emit(snapshot)
