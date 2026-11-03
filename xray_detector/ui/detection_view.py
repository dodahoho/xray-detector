"""DetectionView – split screen av två videoströmmar med detektions-overlay.

Visar nyaste frame per stream med rektanglar + klass + conf. Fångaknapp
(tangent F) tar nyaste frame + detektioner och byter till annoteringsläge.
"""
from __future__ import annotations

import time

import cv2
import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
)

from xray_detector.detection.model_registry import Detection


class StreamLabel(QLabel):
    """Visar ett frame med detektions-overlay."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._pixmap: QPixmap | None = None
        self._dets: list[Detection] = []
        self._fps = 0.0
        self._last_frame_time = 0.0
        self._fps_counter = 0
        self._fps_time = time.time()
        self._show_placeholder()

    def _show_placeholder(self) -> None:
        self.setText(f"{self.title}\n(väntar på video...)")
        self.setStyleSheet("color: #888; font-size: 16px; background: #111;")

    def update_frame(self, frame: np.ndarray, dets: list[Detection]) -> None:
        """Uppdatera med nytt frame + detektioner."""
        if frame is None:
            return
        h, w = frame.shape[:2]
        if frame.ndim == 2:
            rgb = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
        else:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb.data, w, h, w * 3, QImage.Format_RGB888)
        self._pixmap = QPixmap.fromImage(qimg)
        self._dets = dets

        # FPS-mätning
        self._fps_counter += 1
        now = time.time()
        if now - self._fps_time >= 1.0:
            self._fps = self._fps_counter / (now - self._fps_time)
            self._fps_counter = 0
            self._fps_time = now

        self.update()

    def paintEvent(self, event) -> None:
        if self._pixmap is None:
            super().paintEvent(event)
            return
        painter = QPainter(self)
        # Skala pixmapen till widgetens storlek (keep aspect)
        target = self.rect()
        scaled = self._pixmap.scaled(
            target.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        # Centrerat
        x = (target.width() - scaled.width()) // 2
        y = (target.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)

        # Overlay: skala detektioner till pixmapens position
        scale_x = scaled.width() / self._pixmap.width()
        scale_y = scaled.height() / self._pixmap.height()
        pen = QPen(QColor(0, 220, 0), 2)
        painter.setPen(pen)
        font = QFont("Arial", 9)
        painter.setFont(font)
        for d in self._dets:
            rx = x + d.x1 * scale_x
            ry = y + d.y1 * scale_y
            rw = (d.x2 - d.x1) * scale_x
            rh = (d.y2 - d.y1) * scale_y
            painter.drawRect(int(rx), int(ry), int(rw), int(rh))
            label = f"{d.class_name} {d.conf:.2f}"
            # Etikett
            tw = painter.fontMetrics().horizontalAdvance(label)
            th = painter.fontMetrics().height()
            ly = ry - th - 2
            if ly < y:
                ly = ry + 2
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 220, 0, 200))
            painter.drawRect(int(rx), int(ly), tw + 6, th + 2)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(int(rx + 3), int(ly + th), label)
        # FPS
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(x + 6, y + 16, f"{self.title}  {self._fps:.0f} fps")
        painter.end()

    @property
    def fps(self) -> float:
        return self._fps


class DetectionView(QWidget):
    """Detektionsläget: split screen + fånga-knapp."""

    capture_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)

        # Split screen
        split = QHBoxLayout()
        self.left = StreamLabel("Vänster")
        self.right = StreamLabel("Höger")
        split.addWidget(self.left)
        split.addWidget(self.right)
        root.addLayout(split, stretch=1)

        # Kontrollrad
        ctrl = QHBoxLayout()
        self.capture_btn = QPushButton("Fånga bilder (F)")
        self.capture_btn.clicked.connect(self.capture_requested.emit)
        self.status_label = QLabel("")
        ctrl.addWidget(self.capture_btn)
        ctrl.addStretch(1)
        ctrl.addWidget(self.status_label)
        root.addLayout(ctrl)

    def set_left(self, frame: np.ndarray, dets: list[Detection]) -> None:
        self.left.update_frame(frame, dets)

    def set_right(self, frame: np.ndarray, dets: list[Detection]) -> None:
        self.right.update_frame(frame, dets)

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_F:
            self.capture_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)
