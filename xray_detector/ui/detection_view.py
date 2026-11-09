from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from xray_detector.application.video_service import VideoService
from xray_detector.domain.capture import StreamFrame
from xray_detector.domain.config import AppConfig

NO_SOURCE = "Ingen videokälla"
OPEN_FILE = "Öppna videofil..."
UVC_PREFIX = "UVC "

from xray_detector.ui.colors import class_color


class StreamPanel(QFrame):
    source_requested = Signal(str, str, object)

    def __init__(self, source_id: str, title: str, parent=None) -> None:
        super().__init__(parent)
        self.source_id = source_id
        self.known_classes: list[str] = []
        self.latest: StreamFrame | None = None
        self._active: tuple[str, object] = ("none", None)
        self.setMinimumSize(2, 2)
        self.setFrameShape(QFrame.Shape.Box)
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("", 12, QFont.Weight.Bold))
        self.source_combo = QComboBox()
        self.source_combo.addItem(NO_SOURCE)
        self.source_combo.addItem(f"{UVC_PREFIX}0")
        self.source_combo.addItem(f"{UVC_PREFIX}1")
        self.source_combo.addItem(OPEN_FILE)
        self.source_combo.currentTextChanged.connect(self._on_source_changed)
        top.addWidget(self.title_label)
        top.addStretch(1)
        top.addWidget(self.source_combo)
        layout.addLayout(top)
        self.display = QLabel()
        self.display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.display, 1)
        self._show_no_source()

    def _on_source_changed(self, text: str) -> None:
        if text == NO_SOURCE:
            self._active = ("none", None)
            self.source_requested.emit(self.source_id, "none", None)
            self._show_no_source()
        elif text == OPEN_FILE:
            path, _ = QFileDialog.getOpenFileName(
                self, "Välj videofil", "", "Videofiler (*.mp4 *.avi *.mkv *.mov)"
            )
            if path:
                self._active = ("file", path)
                self.source_requested.emit(self.source_id, "file", Path(path))
                self.source_combo.setItemText(self.source_combo.currentIndex(), Path(path).name)
            else:
                self.source_combo.setCurrentIndex(0)
        elif text.startswith(UVC_PREFIX):
            index = int(text.removeprefix(UVC_PREFIX))
            self._active = ("uvc", index)
            self.source_requested.emit(self.source_id, "uvc", index)
        self.latest = None

    def current_source(self) -> tuple[str, object]:
        return self._active

    def restore_source(self, kind: str, value) -> None:
        if kind == "uvc" and value is not None:
            index = self.source_combo.findText(f"{UVC_PREFIX}{value}")
            if index >= 0:
                self.source_combo.setCurrentIndex(index)
        elif kind == "file" and value:
            open_index = self.source_combo.findText(OPEN_FILE)
            if open_index >= 0:
                self.source_combo.setItemText(open_index, Path(value).name)
                self.source_combo.setCurrentIndex(open_index)
                self._active = ("file", value)
                self.source_requested.emit(self.source_id, "file", Path(value))
        else:
            self.source_combo.setCurrentIndex(0)

    def _show_no_source(self) -> None:
        self.display.setText(NO_SOURCE)
        self.display.setStyleSheet("color: #888; font-size: 24px; background: #222;")
        self.latest = None

    def show_frame(self, stream_frame: StreamFrame) -> None:
        self.latest = stream_frame
        image = self._to_qimage(stream_frame.frame)
        painter = QPainter(image)
        pen = QPen()
        pen.setWidth(2)
        font = QFont()
        font.setPointSize(10)
        for detection in stream_frame.detections:
            color = class_color(detection.class_name, self.known_classes)
            pen.setColor(color)
            painter.setPen(pen)
            painter.drawRect(
                int(detection.x1),
                int(detection.y1),
                int(detection.width),
                int(detection.height),
            )
            painter.setFont(font)
            painter.drawText(
                int(detection.x1),
                max(12, int(detection.y1) - 4),
                f"{detection.class_name} {detection.confidence * 100:.0f}%",
            )
        painter.end()
        scaled = QPixmap.fromImage(image).scaled(
            self.display.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.display.setPixmap(scaled)

    def show_source_lost(self) -> None:
        self._show_no_source()

    def clear_overlay(self) -> None:
        if self.latest is not None:
            self.latest.detections = []
            self.show_frame(self.latest)

    @staticmethod
    def _to_qimage(frame: np.ndarray) -> QImage:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channels = rgb.shape
        return QImage(
            rgb.data, width, height, channels * width, QImage.Format.Format_RGB888
        )


class DetectionView(QWidget):
    capture_requested = Signal(object)
    error_occurred = Signal(str)

    def __init__(self, config: AppConfig, settings, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.settings = settings
        self.video_service = VideoService()
        self.detector = None
        layout = QVBoxLayout(self)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Modell:"))
        self.model_combo = QComboBox()
        self.refresh_models()
        index = self.model_combo.findData(config.default_model)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)
        bar.addWidget(self.model_combo)
        bar.addWidget(QLabel("Tröskel:"))
        self.conf_spin = QDoubleSpinBox()
        self.conf_spin.setRange(0.05, 0.95)
        self.conf_spin.setSingleStep(0.05)
        self.conf_spin.setValue(config.confidence_threshold)
        self.conf_spin.valueChanged.connect(self._on_model_changed)
        bar.addWidget(self.conf_spin)
        self.device_label = QLabel("Enhet: kontrollerar...")
        self.device_label.setStyleSheet("font-weight: bold;")
        bar.addWidget(self.device_label)
        bar.addStretch(1)
        self.capture_button = QPushButton("Fånga bilder")
        self.capture_button.setMinimumHeight(40)
        self.capture_button.clicked.connect(self._on_capture)
        bar.addWidget(self.capture_button)
        layout.addLayout(bar)
        panels = QHBoxLayout()
        self.left = StreamPanel("left", "Ström 1")
        self.right = StreamPanel("right", "ström 2")
        for panel in (self.left, self.right):
            panel.known_classes = list(config.classes)
        for panel in (self.left, self.right):
            panel.source_requested.connect(self._on_source_requested)
            panels.addWidget(panel, 1)
        layout.addLayout(panels, 1)

    def refresh_models(self) -> None:
        """Fyller modellväljaren med statiska specar plus nytränade modeller."""
        from xray_detector.application.model_registry import MODEL_SPECS, trained_models

        current = self.model_combo.currentData()
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self._specs = {}
        for spec in MODEL_SPECS:
            self.model_combo.addItem(spec.label, spec.key)
            self._specs[spec.key] = spec
        for spec in trained_models(self.config.models_dir):
            self.model_combo.addItem(spec.label, spec.key)
            self._specs[spec.key] = spec
        index = self.model_combo.findData(current) if current else -1
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
        self.model_combo.blockSignals(False)

    def restore_settings(self) -> None:
        model_key = self.settings.value("detection/model", type=str)
        if model_key:
            index = self.model_combo.findData(model_key)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
        confidence = self.settings.value("detection/confidence", type=float)
        if confidence:
            self.conf_spin.setValue(confidence)
        for panel in (self.left, self.right):
            kind = self.settings.value(f"detection/source_{panel.source_id}_kind", type=str)
            value = self.settings.value(f"detection/source_{panel.source_id}_value")
            if kind:
                panel.restore_source(kind, value)

    def save_settings(self) -> None:
        self.settings.setValue("detection/model", self.model_combo.currentData())
        self.settings.setValue("detection/confidence", self.conf_spin.value())
        for panel in (self.left, self.right):
            kind, value = panel.current_source()
            self.settings.setValue(f"detection/source_{panel.source_id}_kind", kind)
            self.settings.setValue(f"detection/source_{panel.source_id}_value", value)

    def _on_source_requested(self, source_id: str, kind: str, value: object) -> None:
        worker = self.video_service.set_source(source_id, kind, value)
        if worker is not None:
            worker.frame_ready.connect(self._on_frame)
            worker.source_lost.connect(self._on_source_lost)
            worker.error_occurred.connect(self._on_error)
            worker.set_detector(self.detector)

    def _on_frame(self, stream_frame: StreamFrame) -> None:
        panel = self.left if stream_frame.source_id == "left" else self.right
        panel.show_frame(stream_frame)

    def _on_source_lost(self, source_id: str) -> None:
        panel = self.left if source_id == "left" else self.right
        panel.show_source_lost()

    def _on_error(self, source_id: str, message: str) -> None:
        self.error_occurred.emit(f"Detektorfel ({source_id}): {message}")

    def _on_model_changed(self) -> None:
        from xray_detector.application.model_registry import create_detector

        self.error_occurred.emit("Laddar modell...")
        try:
            spec = self._specs[self.model_combo.currentData()]
            self.detector = create_detector(
                spec, self.config.classes, self.conf_spin.value()
            )
            self.video_service.set_detector(self.detector)
            device_label = getattr(self.detector, "device_label", "")
            if device_label:
                self.device_label.setText(f"Enhet: {device_label}")
            self.error_occurred.emit(f"Modell laddad: {spec.label}")
        except Exception as exc:
            self.detector = None
            self.video_service.set_detector(None)
            self.error_occurred.emit(f"Kunde inte ladda modell: {exc}")

    def check_device(self) -> None:
        from xray_detector.application.model_registry import device_status

        text, color = device_status()
        self.device_label.setText(text)
        self.device_label.setStyleSheet(f"font-weight: bold; color: {color};")

    def _on_capture(self) -> None:
        captures: list[StreamFrame] = []
        for panel in (self.left, self.right):
            if panel.latest is not None:
                captures.append(panel.latest)
        if not captures:
            self.error_occurred.emit("Ingen videokälla att fånga ifrån")
            return
        self.capture_requested.emit(captures)

    def pause_detection(self) -> None:
        self.video_service.set_detector(None)
        for panel in (self.left, self.right):
            panel.clear_overlay()

    def resume_detection(self) -> None:
        if self.detector is not None:
            self.video_service.set_detector(self.detector)

    def stop(self) -> None:
        self.video_service.stop_all()
