"""Video preview widget with detection overlays."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from xray_detector.domain.detection import Detection, FramePacket

CLASS_COLORS = [
    QColor(255, 99, 71),
    QColor(64, 224, 208),
    QColor(255, 215, 0),
    QColor(147, 112, 219),
    QColor(60, 179, 113),
    QColor(255, 140, 0),
    QColor(70, 130, 180),
    QColor(220, 20, 60),
]


def class_color(name: str) -> QColor:
    import zlib

    return CLASS_COLORS[zlib.crc32(name.encode("utf-8")) % len(CLASS_COLORS)]


def bgr_to_qimage(frame) -> QImage:
    import cv2

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    height, width, channels = rgb.shape
    return QImage(
        rgb.data,
        width,
        height,
        channels * width,
        QImage.Format.Format_RGB888,
    ).copy()


class VideoPanel(QWidget):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.title = title
        self._image: QImage | None = None
        self._image_size = (0, 0)
        self._frame_sequence = 0
        self._detections: list[Detection] = []
        self._detection_sequence = 0
        self._status = "Inte ansluten"
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background-color: #101014;")

    def set_frame(self, packet: FramePacket) -> None:
        if packet.sequence < self._frame_sequence:
            return
        try:
            self._image = bgr_to_qimage(packet.frame)
            self._image_size = (packet.frame.shape[1], packet.frame.shape[0])
            self._frame_sequence = packet.sequence
            if self._detection_sequence > self._frame_sequence:
                self._detections = []
        except Exception:
            return
        self.update()

    def set_detections(self, sequence: int, detections: list[Detection]) -> None:
        if sequence < self._detection_sequence:
            return
        self._detection_sequence = sequence
        self._detections = list(detections)
        self.update()

    def set_status(self, message: str) -> None:
        self._status = message
        self.update()

    def clear(self) -> None:
        self._image = None
        self._detections = []
        self._frame_sequence = 0
        self._detection_sequence = 0
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#101014"))

        if self._image is None or self._image.isNull():
            painter.setPen(QColor("#8a8a96"))
            font = QFont()
            font.setPointSize(13)
            painter.setFont(font)
            painter.drawText(
                self.rect(), Qt.AlignmentFlag.AlignCenter, f"{self.title}\n{self._status}"
            )
            painter.end()
            return

        target = self._fitted_rect()
        painter.drawImage(target, self._image)

        source_width, source_height = self._image_size
        scale_x = target.width() / max(1, source_width)
        scale_y = target.height() / max(1, source_height)
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        metrics = painter.fontMetrics()

        for detection in self._detections:
            if detection.score < 0.05:
                continue
            bbox = detection.bbox
            rect = QRectF(
                target.left() + bbox.x1 * scale_x,
                target.top() + bbox.y1 * scale_y,
                max(1.0, bbox.width * scale_x),
                max(1.0, bbox.height * scale_y),
            )
            color = class_color(detection.class_name)
            painter.setPen(QPen(color, 2))
            painter.drawRect(rect)
            label = f"{detection.class_name} {detection.score:.2f}"
            text_rect = metrics.boundingRect(label).adjusted(-4, -2, 4, 2)
            label_rect = QRectF(
                rect.left(),
                max(target.top(), rect.top() - text_rect.height()),
                text_rect.width(),
                text_rect.height(),
            )
            painter.fillRect(label_rect, QColor(color.red(), color.green(), color.blue(), 210))
            painter.setPen(QColor("#101014"))
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, label)

        painter.setPen(QColor(230, 230, 230))
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(
            target.adjusted(10, 8, -10, -8),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            self.title,
        )
        painter.end()

    def _fitted_rect(self) -> QRectF:
        if self._image is None:
            return QRectF(self.rect())
        image_aspect = self._image.width() / max(1, self._image.height())
        widget_aspect = self.width() / max(1, self.height())
        if widget_aspect > image_aspect:
            height = self.height()
            width = height * image_aspect
            left = (self.width() - width) / 2
            return QRectF(left, 0, width, height)
        width = self.width()
        height = width / image_aspect
        top = (self.height() - height) / 2
        return QRectF(0, top, width, height)
