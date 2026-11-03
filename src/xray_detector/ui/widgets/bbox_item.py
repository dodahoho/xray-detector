"""Editable bounding-box graphics item with resize handles."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject

from xray_detector.domain.annotation import AnnotationBox
from xray_detector.domain.detection import BBox

HANDLE_NAMES = ("tl", "t", "tr", "r", "br", "b", "bl", "l")
HANDLE_CURSORS = (
    Qt.CursorShape.SizeFDiagCursor,
    Qt.CursorShape.SizeVerCursor,
    Qt.CursorShape.SizeBDiagCursor,
    Qt.CursorShape.SizeHorCursor,
    Qt.CursorShape.SizeFDiagCursor,
    Qt.CursorShape.SizeVerCursor,
    Qt.CursorShape.SizeBDiagCursor,
    Qt.CursorShape.SizeHorCursor,
)


class BBoxItem(QGraphicsObject):
    geometry_changed = Signal()

    def __init__(
        self,
        rect: QRectF,
        class_name: str,
        color: QColor,
        image_rect: QRectF,
        score: float | None = None,
        parent: QGraphicsItem | None = None,
    ) -> None:
        super().__init__(parent)
        self._rect = QRectF(rect).normalized()
        self.class_name = class_name
        self.color = QColor(color)
        self.image_rect = QRectF(image_rect)
        self.score = score
        self._drag_mode: int | None = None
        self._start_rect = QRectF()
        self._start_pos = QPointF()
        self._min_size = 4.0
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(10)

    def boundingRect(self) -> QRectF:  # noqa: N802
        margin = 60.0 / max(0.05, self._view_scale())
        return self._rect.adjusted(-margin, -margin, margin, margin)

    def shape(self):
        from PySide6.QtGui import QPainterPath

        path = QPainterPath()
        path.addRect(self._rect)
        return path

    def paint(self, painter, option, widget=None) -> None:
        scale = self._view_scale()
        handle_size = 8.0 / scale
        pen = QPen(self.color, 2)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(self._rect)

        if self.isSelected():
            painter.setPen(QPen(QColor("#ffffff"), 1))
            painter.setBrush(self.color)
            for point in self._handle_points():
                painter.drawEllipse(point, handle_size / 2, handle_size / 2)

        label = self.class_name
        if self.score is not None:
            label = f"{label} {self.score:.2f}"
        font = QFont()
        font.setPointSizeF(max(1.0, 10.0 / scale))
        font.setBold(True)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(label) + 8
        text_height = metrics.height() + 2
        label_rect = QRectF(
            self._rect.left(),
            max(0.0, self._rect.top() - text_height),
            text_width,
            text_height,
        )
        painter.fillRect(
            label_rect, QColor(self.color.red(), self.color.green(), self.color.blue(), 220)
        )
        painter.setPen(QColor("#101014"))
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, label)

    def _view_scale(self) -> float:
        scene = self.scene()
        if scene is not None and scene.views():
            return max(0.05, abs(scene.views()[0].transform().m11()))
        return 1.0

    def _handle_points(self) -> list[QPointF]:
        rect = self._rect
        cx = rect.center().x()
        cy = rect.center().y()
        return [
            rect.topLeft(),
            QPointF(cx, rect.top()),
            rect.topRight(),
            QPointF(rect.right(), cy),
            rect.bottomRight(),
            QPointF(cx, rect.bottom()),
            rect.bottomLeft(),
            QPointF(rect.left(), cy),
        ]

    def _handle_at(self, pos: QPointF) -> int | None:
        handle_size = 8.0 / self._view_scale()
        radius = max(handle_size, 3.0) / 2 + 2.0 / self._view_scale()
        for index, point in enumerate(self._handle_points()):
            if abs(pos.x() - point.x()) <= radius and abs(pos.y() - point.y()) <= radius:
                return index
        return None

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return
        if self.scene() is not None:
            self.scene().clearSelection()
        self.setSelected(True)
        pos = event.pos()
        handle = self._handle_at(pos)
        if handle is not None:
            self._drag_mode = handle
        elif self._rect.contains(pos):
            self._drag_mode = -1
        else:
            self._drag_mode = None
            event.ignore()
            return
        self._start_rect = QRectF(self._rect)
        self._start_pos = pos
        event.accept()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_mode is None:
            event.ignore()
            return
        pos = event.pos()
        delta = pos - self._start_pos
        rect = QRectF(self._start_rect)
        mode = self._drag_mode
        if mode == -1:
            rect.translate(delta)
            rect = self._constrain_translation(rect)
        else:
            left, top, right, bottom = rect.left(), rect.top(), rect.right(), rect.bottom()
            if mode in (0, 6, 7):
                left += delta.x()
            if mode in (2, 3, 4):
                right += delta.x()
            if mode in (0, 1, 2):
                top += delta.y()
            if mode in (4, 5, 6):
                bottom += delta.y()
            rect = QRectF(QPointF(left, top), QPointF(right, bottom)).normalized()
            if rect.width() < self._min_size:
                if mode in (0, 6, 7):
                    rect.setLeft(rect.right() - self._min_size)
                else:
                    rect.setRight(rect.left() + self._min_size)
            if rect.height() < self._min_size:
                if mode in (0, 1, 2):
                    rect.setTop(rect.bottom() - self._min_size)
                else:
                    rect.setBottom(rect.top() + self._min_size)
            rect = self._constrain_rect(rect)
        self.prepareGeometryChange()
        self._rect = rect
        self.geometry_changed.emit()
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag_mode = None
        event.accept()

    def hoverMoveEvent(self, event) -> None:  # noqa: N802
        handle = self._handle_at(event.pos())
        if handle is not None:
            self.setCursor(HANDLE_CURSORS[handle])
        elif self._rect.contains(event.pos()):
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverMoveEvent(event)

    def _constrain_translation(self, rect: QRectF) -> QRectF:
        dx = 0.0
        dy = 0.0
        if rect.left() < self.image_rect.left():
            dx = self.image_rect.left() - rect.left()
        elif rect.right() > self.image_rect.right():
            dx = self.image_rect.right() - rect.right()
        if rect.top() < self.image_rect.top():
            dy = self.image_rect.top() - rect.top()
        elif rect.bottom() > self.image_rect.bottom():
            dy = self.image_rect.bottom() - rect.bottom()
        rect.translate(dx, dy)
        return rect

    def _constrain_rect(self, rect: QRectF) -> QRectF:
        left = max(self.image_rect.left(), rect.left())
        top = max(self.image_rect.top(), rect.top())
        right = min(self.image_rect.right(), rect.right())
        bottom = min(self.image_rect.bottom(), rect.bottom())
        return QRectF(QPointF(left, top), QPointF(right, bottom)).normalized()

    def set_class_name(self, class_name: str, color: QColor | None = None) -> None:
        self.class_name = class_name
        if color is not None:
            self.color = QColor(color)
        self.update()

    def set_rect(self, rect: QRectF) -> None:
        self.prepareGeometryChange()
        self._rect = QRectF(rect).normalized()
        self.update()

    def rect(self) -> QRectF:
        return QRectF(self._rect)

    def to_annotation(self) -> AnnotationBox:
        return AnnotationBox(
            bbox=BBox(self._rect.left(), self._rect.top(), self._rect.right(), self._rect.bottom()),
            class_name=self.class_name,
            score=self.score,
        )
