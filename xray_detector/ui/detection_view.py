"""DetectionView – split screen av två videoströmmar med detektions-overlay.

Visar nyaste frame per stream med rektanglar + klass + conf. Fångaknapp
(tangent F) tar nyaste frame + detektioner och byter till annoteringsläge.
"""
from __future__ import annotations

import time

import cv2
import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from xray_detector.detection.model_registry import Detection


class StreamLabel(QLabel):
    """Visar ett frame med detektions-overlay."""

    retry_requested = Signal()

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._pixmap: QPixmap | None = None
        self._dets: list[Detection] = []
        self._error_text: str | None = None
        self._fps = 0.0
        self._last_frame_time = 0.0
        self._fps_counter = 0
        self._fps_time = time.time()

        # Knapp som visas i videofönstret när källan inte kunde anslutas.
        self._retry_btn = QPushButton("Försök igen", self)
        self._retry_btn.setCursor(Qt.PointingHandCursor)
        self._retry_btn.setStyleSheet(
            "QPushButton {"
            " color: #fff; background: #b33939; border: 1px solid #e06c6c;"
            " border-radius: 4px; padding: 8px 18px; font-size: 14px;"
            "}"
            "QPushButton:hover { background: #d64545; }"
            "QPushButton:pressed { background: #8f2b2b; }"
        )
        self._retry_btn.clicked.connect(self.retry_requested.emit)
        self._retry_btn.setVisible(False)
        self._show_placeholder()

    def _show_placeholder(self) -> None:
        self.setText(f"{self.title}\n(väntar på video...)")
        self.setStyleSheet("color: #888; font-size: 16px; background: #111;")

    def show_connecting(self, attempt: int = 0, max_attempts: int = 0) -> None:
        """Visa att ett anslutningsförsök pågår (utan retry-knapp)."""
        self._pixmap = None
        self._dets = []
        self._error_text = None
        self._retry_btn.setVisible(False)
        if attempt and max_attempts:
            message = f"Ansluter till videokälla... (försök {attempt}/{max_attempts})"
        else:
            message = "Ansluter till videokälla..."
        self.setText(f"{self.title}\n{message}")
        self.setStyleSheet(
            "color: #e0b341; font-size: 16px; background: #000;"
        )
        self.update()

    def show_error(self, message: str = "Ingen videokälla") -> None:
        """Visa svart skärm med felmeddelande och en manuell retry-knapp."""
        self._pixmap = None
        self._dets = []
        self._error_text = message
        self.setText(f"{self.title}\n{message}")
        self.setStyleSheet(
            "color: #ff6b6b; font-size: 18px; background: #000;"
        )
        self._retry_btn.setVisible(True)
        self._position_retry_button()
        self.update()

    def clear_error(self) -> None:
        if self._error_text is None and self._retry_btn.isHidden():
            return
        self._error_text = None
        self._retry_btn.setVisible(False)
        self.setStyleSheet("background: #000;")
        self.update()

    def _position_retry_button(self) -> None:
        if self._retry_btn.isHidden():
            return
        self._retry_btn.adjustSize()
        x = max(0, (self.width() - self._retry_btn.width()) // 2)
        y = min(
            self.height() // 2 + 28,
            self.height() - self._retry_btn.height() - 8,
        )
        self._retry_btn.move(x, max(0, y))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_retry_button()

    def update_frame(self, frame: np.ndarray, dets: list[Detection]) -> None:
        """Uppdatera med nytt frame + detektioner."""
        if frame is None:
            return
        self.clear_error()
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
    stream_retry_requested = Signal(int)

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
        self.left.retry_requested.connect(
            lambda: self.stream_retry_requested.emit(0)
        )
        self.right.retry_requested.connect(
            lambda: self.stream_retry_requested.emit(1)
        )
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

    def set_stream_connecting(
        self, index: int, attempt: int = 0, max_attempts: int = 0
    ) -> None:
        """Visa pågående anslutningsförsök för en ström."""
        label = self.left if index == 0 else self.right
        label.show_connecting(attempt, max_attempts)

    def set_stream_error(self, index: int, message: str = "Ingen videokälla") -> None:
        """Visa fel/svart skärm för en enskild ström (0 = vänster, 1 = höger)."""
        label = self.left if index == 0 else self.right
        label.show_error(message)

    def set_stream_ok(self, index: int) -> None:
        """Återställ en ström efter att video återigen tagits emot."""
        label = self.left if index == 0 else self.right
        label.clear_error()

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_F:
            self.capture_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)
