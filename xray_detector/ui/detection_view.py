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

from xray_detector.capture.camera_service import CameraService, StreamFrame
from xray_detector.config import AppConfig
from xray_detector.detection.base import BaseDetector, Detection

NO_SOURCE = "Ingen videokälla"
OPEN_FILE = "Öppna videofil..."
UVC_PREFIX = "UVC "

CLASS_COLORS = [
    QColor(255, 80, 80),
    QColor(80, 200, 120),
    QColor(80, 140, 255),
    QColor(255, 200, 60),
    QColor(220, 100, 255),
]


class StreamPanel(QFrame):
    source_requested = Signal(str, str, object)

    def __init__(self, source_id: str, title: str, parent=None) -> None:
        super().__init__(parent)
        self.source_id = source_id
        self.latest: StreamFrame | None = None
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
            self.source_requested.emit(self.source_id, "none", None)
            self._show_no_source()
        elif text == OPEN_FILE:
            path, _ = QFileDialog.getOpenFileName(
                self, "Välj videofil", "", "Videofiler (*.mp4 *.avi *.mkv *.mov)"
            )
            if path:
                self.source_requested.emit(self.source_id, "file", Path(path))
                self.source_combo.setItemText(self.source_combo.currentIndex(), Path(path).name)
            else:
                self.source_combo.setCurrentIndex(0)
        elif text.startswith(UVC_PREFIX):
            index = int(text.removeprefix(UVC_PREFIX))
            self.source_requested.emit(self.source_id, "uvc", index)
        self.latest = None

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
            color = CLASS_COLORS[hash(detection.class_name) % len(CLASS_COLORS)]
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

    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.camera_service = CameraService()
        self.detector: BaseDetector | None = None
        layout = QVBoxLayout(self)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Modell:"))
        self.model_combo = QComboBox()
        from xray_detector.detection.registry import MODEL_SPECS

        for spec in MODEL_SPECS:
            self.model_combo.addItem(spec.label, spec.key)
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
            panel.source_requested.connect(self._on_source_requested)
            panels.addWidget(panel, 1)
        layout.addLayout(panels, 1)

    def _on_source_requested(self, source_id: str, kind: str, value: object) -> None:
        from xray_detector.capture.source import FileSource, UvcSource

        source = None
        if kind == "uvc":
            source = UvcSource(int(value))
        elif kind == "file":
            source = FileSource(Path(value))
        worker = self.camera_service.set_source(source_id, source)
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
        from xray_detector.detection.registry import create_detector, spec_by_key

        self.error_occurred.emit("Laddar modell...")
        try:
            spec = spec_by_key(self.model_combo.currentData())
            self.detector = create_detector(
                spec, self.config.classes, self.conf_spin.value()
            )
            self.camera_service.set_detector(self.detector)
            device_label = getattr(self.detector, "device_label", "")
            suffix = f" – {device_label}" if device_label else ""
            self.error_occurred.emit(f"Modell laddad: {spec.label}{suffix}")
        except Exception as exc:
            self.detector = None
            self.camera_service.set_detector(None)
            self.error_occurred.emit(f"Kunde inte ladda modell: {exc}")

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
        self.camera_service.set_detector(None)
        for panel in (self.left, self.right):
            panel.clear_overlay()

    def resume_detection(self) -> None:
        if self.detector is not None:
            self.camera_service.set_detector(self.detector)

    def stop(self) -> None:
        self.camera_service.stop_all()
