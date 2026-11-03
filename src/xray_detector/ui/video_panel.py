from __future__ import annotations

import numpy as np
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen
from PySide6.QtWidgets import QWidget

from xray_detector.models import Detection


class VideoPanel(QWidget):
    def __init__(self, title: str, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.title = title
        self._image: QImage | None = None
        self._frame: np.ndarray | None = None
        self._detections: list[Detection] = []
        self._message = "Väntar på video..."
        self.setMinimumSize(320, 240)
        self.setAutoFillBackground(False)

    def set_frame(self, frame: np.ndarray) -> None:
        if frame is None or frame.size == 0:
            return
        height, width = frame.shape[:2]
        image = QImage(
            frame.data,
            width,
            height,
            int(frame.strides[0]),
            QImage.Format.Format_BGR888,
        )
        self._image = image.copy()
        self._frame = frame
        self._message = ""
        self.update()

    def set_detections(self, detections: list[Detection]) -> None:
        self._detections = list(detections)
        self.update()

    def set_message(self, message: str) -> None:
        self._message = message
        self.update()

    @property
    def last_frame(self) -> np.ndarray | None:
        return self._frame

    @property
    def detections(self) -> list[Detection]:
        return list(self._detections)

    def clear(self) -> None:
        self._image = None
        self._frame = None
        self._detections = []
        self._message = "Väntar på video..."
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(18, 18, 18))
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        target = QRectF(self.rect()).adjusted(4, 4, -4, -4)
        if self._image is not None and self._image.width() > 0 and self._image.height() > 0:
            image_ratio = self._image.width() / self._image.height()
            target_ratio = target.width() / target.height() if target.height() else image_ratio
            if image_ratio > target_ratio:
                new_height = target.width() / image_ratio
                target = QRectF(
                    target.left(),
                    target.top() + (target.height() - new_height) / 2,
                    target.width(),
                    new_height,
                )
            else:
                new_width = target.height() * image_ratio
                target = QRectF(
                    target.left() + (target.width() - new_width) / 2,
                    target.top(),
                    new_width,
                    target.height(),
                )
            painter.drawImage(target, self._image)
            self._paint_detections(painter, target)

        painter.setPen(QColor(235, 235, 235))
        font = QFont(self.font())
        font.setPointSize(11)
        font.setBold(True)
        painter.setFont(font)
        painter.fillRect(QRectF(10, 10, 190, 26), QColor(0, 0, 0, 160))
        painter.drawText(QRectF(16, 10, 180, 26), Qt.AlignmentFlag.AlignVCenter, self.title)
        if self._message:
            font.setPointSize(14)
            font.setBold(False)
            painter.setFont(font)
            painter.setPen(QColor(200, 200, 200))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                self._message,
            )

    def _paint_detections(self, painter: QPainter, target: QRectF) -> None:
        if self._image is None:
            return
        sx = target.width() / self._image.width()
        sy = target.height() / self._image.height()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        font = QFont(self.font())
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)
        for detection in self._detections:
            x1 = target.left() + detection.x1 * sx
            y1 = target.top() + detection.y1 * sy
            x2 = target.left() + detection.x2 * sx
            y2 = target.top() + detection.y2 * sy
            pen = QPen(QColor(70, 255, 130), 2.0)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRectF(x1, y1, x2 - x1, y2 - y1))
            label = f"{detection.class_name} {detection.confidence:.2f}"
            metrics = painter.fontMetrics()
            width = metrics.horizontalAdvance(label) + 8
            height = metrics.height() + 2
            label_rect = QRectF(x1, max(y1 - height, target.top()), width, height)
            painter.fillRect(label_rect, QColor(10, 80, 30, 220))
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(
                label_rect.adjusted(4, 0, -4, 0),
                Qt.AlignmentFlag.AlignVCenter,
                label,
            )
