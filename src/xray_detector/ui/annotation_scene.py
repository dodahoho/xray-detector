from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QFrame,
)

from xray_detector.models import Detection

HANDLE_SIZE = 7.0
MIN_BOX_SIZE = 4.0
NORMAL_PEN = QColor(80, 220, 120)
SELECTED_PEN = QColor(255, 210, 70)


class BoxItem(QGraphicsRectItem):
    def __init__(
        self,
        rect: QRectF,
        class_name: str,
        class_id: int = 0,
        confidence: float = 1.0,
        on_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(rect)
        self.class_name = class_name
        self.class_id = class_id
        self.confidence = confidence
        self._on_changed = on_changed
        self._resize_mode: str | None = None
        self._press_local = QPointF()
        self._original_rect = QRectF()
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setZValue(10.0)
        self.setBrush(QBrush(QColor(80, 220, 120, 28)))
        self._apply_style()

    def _apply_style(self) -> None:
        color = SELECTED_PEN if self.isSelected() else NORMAL_PEN
        pen = QPen(color, 2.0)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.setBrush(QBrush(QColor(color.red(), color.green(), color.blue(), 28)))

    def _scale(self) -> float:
        views = self.scene().views() if self.scene() else []
        if not views:
            return 1.0
        scale = views[0].transform().m11()
        return scale if scale > 0 else 1.0

    def _tolerance(self) -> float:
        return HANDLE_SIZE / self._scale()

    def handle_rects(self) -> dict[str, QRectF]:
        rect = self.rect()
        size = HANDLE_SIZE / self._scale()
        points = {
            "tl": rect.topLeft(),
            "t": QPointF(rect.center().x(), rect.top()),
            "tr": rect.topRight(),
            "r": QPointF(rect.right(), rect.center().y()),
            "br": rect.bottomRight(),
            "b": QPointF(rect.center().x(), rect.bottom()),
            "bl": rect.bottomLeft(),
            "l": QPointF(rect.left(), rect.center().y()),
        }
        return {
            key: QRectF(point.x() - size / 2, point.y() - size / 2, size, size)
            for key, point in points.items()
        }

    def _handle_at(self, point: QPointF) -> str | None:
        for name, rect in self.handle_rects().items():
            if rect.contains(point):
                return name
        return None

    def hoverMoveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        handle = self._handle_at(event.pos())
        cursors = {
            "tl": Qt.CursorShape.SizeFDiagCursor,
            "br": Qt.CursorShape.SizeFDiagCursor,
            "tr": Qt.CursorShape.SizeBDiagCursor,
            "bl": Qt.CursorShape.SizeBDiagCursor,
            "l": Qt.CursorShape.SizeHorCursor,
            "r": Qt.CursorShape.SizeHorCursor,
            "t": Qt.CursorShape.SizeVerCursor,
            "b": Qt.CursorShape.SizeVerCursor,
        }
        if handle:
            self.setCursor(cursors[handle])
        else:
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self._handle_at(event.pos())
            if handle:
                self._resize_mode = handle
                self._press_local = event.pos()
                self._original_rect = QRectF(self.rect())
                self.setSelected(True)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if self._resize_mode:
            local = self.mapFromScene(event.scenePos())
            delta = local - self._press_local
            rect = QRectF(self._original_rect)
            left, top, right, bottom = (
                rect.left(),
                rect.top(),
                rect.right(),
                rect.bottom(),
            )
            mode = self._resize_mode
            if "l" in mode:
                left += delta.x()
            if "r" in mode:
                right += delta.x()
            if "t" in mode:
                top += delta.y()
            if "b" in mode:
                bottom += delta.y()
            if right - left < MIN_BOX_SIZE:
                if "l" in mode:
                    left = right - MIN_BOX_SIZE
                else:
                    right = left + MIN_BOX_SIZE
            if bottom - top < MIN_BOX_SIZE:
                if "t" in mode:
                    top = bottom - MIN_BOX_SIZE
                else:
                    bottom = top + MIN_BOX_SIZE
            scene_rect = self.scene().sceneRect() if self.scene() else QRectF()
            position = self.pos()
            left = max(left, scene_rect.left() - position.x())
            top = max(top, scene_rect.top() - position.y())
            right = min(right, scene_rect.right() - position.x())
            bottom = min(bottom, scene_rect.bottom() - position.y())
            self.prepareGeometryChange()
            self.setRect(QRectF(left, top, max(1.0, right - left), max(1.0, bottom - top)))
            self._notify_changed()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if self._resize_mode:
            self._resize_mode = None
            self._notify_changed()
            event.accept()
            return
        super().mouseReleaseEvent(event)
        self._notify_changed()

    def itemChange(self, change, value):  # type: ignore[no-untyped-def]
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self._apply_style()
        elif change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene():
            scene_rect = self.scene().sceneRect()
            rect = self.rect()
            position = value
            x = min(
                max(position.x(), scene_rect.left() - rect.left()),
                scene_rect.right() - rect.right(),
            )
            y = min(
                max(position.y(), scene_rect.top() - rect.top()),
                scene_rect.bottom() - rect.bottom(),
            )
            return QPointF(x, y)
        return super().itemChange(change, value)

    def _notify_changed(self) -> None:
        if self._on_changed is not None:
            self._on_changed()

    def set_class(self, name: str, class_id: int = 0) -> None:
        self.class_name = name
        self.class_id = class_id
        self.update()

    def to_detection(self) -> Detection:
        rect = self.mapRectToScene(self.rect())
        return Detection(
            x1=rect.left(),
            y1=rect.top(),
            x2=rect.right(),
            y2=rect.bottom(),
            class_id=self.class_id,
            class_name=self.class_name,
            confidence=self.confidence,
        )

    def paint(self, painter: QPainter, option, widget=None) -> None:  # type: ignore[no-untyped-def]
        super().paint(painter, option, widget)
        rect = self.rect()
        label = self.class_name
        if self.confidence < 0.999:
            label = f"{label} {self.confidence:.2f}"
        if not label:
            label = "objekt"
        font = QFont(painter.font())
        font.setPointSizeF(max(7.0, 10.0 / self._scale()))
        painter.setFont(font)
        metrics = painter.fontMetrics()
        width = metrics.horizontalAdvance(label) + 8
        height = metrics.height() + 2
        label_rect = QRectF(rect.left(), max(rect.top() - height, 0.0), width, height)
        painter.fillRect(label_rect, QColor(20, 20, 20, 205))
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(
            label_rect.adjusted(4, 0, -4, 0),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            label,
        )
        if self.isSelected():
            painter.setPen(QPen(SELECTED_PEN, 1.0))
            painter.setBrush(QBrush(SELECTED_PEN))
            for handle in self.handle_rects().values():
                painter.drawRect(handle)


class AnnotationCanvas(QGraphicsView):
    def __init__(self, title: str, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.title = title
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._current_class = ""
        self._draw_enabled = True
        self._drawing = False
        self._draw_start = QPointF()
        self._temp_box: BoxItem | None = None
        self._panning = False
        self._pan_last = QPointF()
        self._image_width = 0
        self._image_height = 0
        self._fit_pending = False

        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setBackgroundBrush(QColor(18, 18, 18))
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setMouseTracking(True)
        self.setMinimumSize(320, 240)

    @property
    def image_size(self) -> tuple[int, int]:
        return self._image_width, self._image_height

    def set_current_class(self, name: str) -> None:
        self._current_class = name.strip()

    def set_draw_enabled(self, enabled: bool) -> None:
        self._draw_enabled = enabled
        self.viewport().setCursor(
            Qt.CursorShape.CrossCursor if enabled else Qt.CursorShape.ArrowCursor
        )

    def load_image(self, path: Path | str) -> None:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            raise ValueError(f"Kunde inte lasa bilden {path}")
        self._scene.clear()
        self._pixmap_item = QGraphicsPixmapItem(pixmap)
        self._pixmap_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self._pixmap_item.setZValue(0)
        self._scene.addItem(self._pixmap_item)
        self._image_width = pixmap.width()
        self._image_height = pixmap.height()
        self._scene.setSceneRect(QRectF(0, 0, self._image_width, self._image_height))
        self._temp_box = None
        self._drawing = False
        self._fit_pending = True
        self.fit_image()

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().resizeEvent(event)
        if self._fit_pending and self.isVisible() and self.width() > 10:
            self.fit_image()
            self._fit_pending = False

    def fit_image(self) -> None:
        if self._image_width and self._image_height:
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def add_detection(self, detection: Detection) -> BoxItem:
        rect = QRectF(
            detection.x1,
            detection.y1,
            max(1.0, detection.x2 - detection.x1),
            max(1.0, detection.y2 - detection.y1),
        )
        item = BoxItem(
            rect,
            detection.class_name,
            detection.class_id,
            detection.confidence,
            on_changed=self.viewport().update,
        )
        self._scene.addItem(item)
        self.viewport().update()
        return item

    def boxes(self) -> list[BoxItem]:
        return [item for item in self._scene.items() if isinstance(item, BoxItem)]

    def selected_boxes(self) -> list[BoxItem]:
        return [item for item in self._scene.selectedItems() if isinstance(item, BoxItem)]

    def delete_selected(self) -> None:
        for item in self.selected_boxes():
            self._scene.removeItem(item)
        self.viewport().update()

    def assign_class(self, name: str) -> int:
        cleaned = name.strip()
        if not cleaned:
            return 0
        selected = self.selected_boxes()
        for item in selected:
            item.set_class(cleaned)
        self.viewport().update()
        return len(selected)

    def detections(self) -> list[Detection]:
        return [item.to_detection() for item in self.boxes()]

    def clear_boxes(self) -> None:
        for item in self.boxes():
            self._scene.removeItem(item)
        self.viewport().update()

    def mousePressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_last = event.position()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton and self._draw_enabled:
            point = self.mapToScene(event.position().toPoint())
            scene_item = self._scene.itemAt(point, self.transform())
            if scene_item is None or isinstance(scene_item, QGraphicsPixmapItem):
                if self._current_class and self._scene.sceneRect().contains(point):
                    self._drawing = True
                    self._draw_start = point
                    self._temp_box = BoxItem(
                        QRectF(point, point),
                        self._current_class,
                        confidence=1.0,
                        on_changed=self.viewport().update,
                    )
                    self._temp_box.setOpacity(0.75)
                    self._scene.addItem(self._temp_box)
                    event.accept()
                    return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if self._panning:
            delta = event.position() - self._pan_last
            self._pan_last = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
            event.accept()
            return
        if self._drawing and self._temp_box is not None:
            point = self.mapToScene(event.position().toPoint())
            rect = QRectF(self._draw_start, point).normalized()
            rect = rect.intersected(self._scene.sceneRect())
            self._temp_box.setRect(rect)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.button() == Qt.MouseButton.MiddleButton and self._panning:
            self._panning = False
            self.set_draw_enabled(self._draw_enabled)
            event.accept()
            return
        if self._drawing and self._temp_box is not None:
            self._drawing = False
            rect = self._temp_box.rect()
            if rect.width() < MIN_BOX_SIZE or rect.height() < MIN_BOX_SIZE:
                self._scene.removeItem(self._temp_box)
            else:
                self._temp_box.setOpacity(1.0)
                self._temp_box.setSelected(True)
            self._temp_box = None
            self.viewport().update()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        current = self.transform().m11()
        new_scale = current * factor
        if 0.02 <= new_scale <= 40.0:
            self.scale(factor, factor)
        event.accept()

    def keyPressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_selected()
            event.accept()
            return
        super().keyPressEvent(event)
