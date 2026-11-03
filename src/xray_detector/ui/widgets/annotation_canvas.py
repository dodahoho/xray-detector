"""Interactive annotation canvas."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsView, QWidget

from xray_detector.domain.annotation import AnnotationBox
from xray_detector.ui.widgets.bbox_item import BBoxItem
from xray_detector.ui.widgets.video_panel import bgr_to_qimage, class_color


class AnnotationCanvas(QGraphicsView):
    selection_changed = Signal(object)
    boxes_changed = Signal()

    def __init__(self, role: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.role = role
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._background: QGraphicsPixmapItem | None = None
        self._image_rect = QRectF(0, 0, 1, 1)
        self._current_class = "object"
        self._drawing: BBoxItem | None = None
        self._draw_start = QPointF()
        self._auto_fit = True

        self.setRenderHints(
            self.renderHints()
            | self.renderHints().Antialiasing
            | self.renderHints().SmoothPixmapTransform
        )
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setBackgroundBrush(QColor("#16161c"))
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self._scene.selectionChanged.connect(self._on_selection_changed)

    def set_image(self, frame: np.ndarray) -> None:
        self._scene.clear()
        self._background = None
        self._drawing = None
        image = bgr_to_qimage(frame)
        pixmap = QPixmap.fromImage(image)
        background = self._scene.addPixmap(pixmap)
        background.setZValue(-10)
        self._background = background
        height, width = frame.shape[:2]
        self._image_rect = QRectF(0, 0, width, height)
        self._scene.setSceneRect(self._image_rect)
        self._auto_fit = True
        self.fit_to_window()

    def fit_to_window(self) -> None:
        if self._background is None:
            return
        self.fitInView(self._image_rect, Qt.AspectRatioMode.KeepAspectRatio)
        self._auto_fit = True

    def set_current_class(self, class_name: str) -> None:
        self._current_class = class_name.strip() or "object"

    def add_box(self, annotation: AnnotationBox) -> BBoxItem:
        bbox = annotation.bbox
        rect = QRectF(bbox.x1, bbox.y1, bbox.width, bbox.height)
        item = BBoxItem(
            rect=rect,
            class_name=annotation.class_name,
            color=class_color(annotation.class_name),
            image_rect=self._image_rect,
            score=annotation.score,
        )
        item.geometry_changed.connect(self.boxes_changed)
        self._scene.addItem(item)
        return item

    def annotations(self) -> list[AnnotationBox]:
        result = []
        for item in self._scene.items():
            if isinstance(item, BBoxItem):
                result.append(item.to_annotation())
        return result

    def selected_box(self) -> BBoxItem | None:
        for item in self._scene.selectedItems():
            if isinstance(item, BBoxItem):
                return item
        return None

    def delete_selected(self) -> bool:
        selected = [item for item in self._scene.selectedItems() if isinstance(item, BBoxItem)]
        for item in selected:
            self._scene.removeItem(item)
        if selected:
            self.boxes_changed.emit()
            self.selection_changed.emit(None)
        return bool(selected)

    def clear_selection(self) -> None:
        self._scene.clearSelection()

    def _on_selection_changed(self) -> None:
        self.selection_changed.emit(self.selected_box())

    def wheelEvent(self, event) -> None:  # noqa: N802
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self.scale(factor, factor)
            self._auto_fit = False
            event.accept()
            return
        super().wheelEvent(event)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._auto_fit:
            self.fit_to_window()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.position().toPoint())
            if not isinstance(item, BBoxItem):
                self._scene.clearSelection()
                self._draw_start = self.mapToScene(event.position().toPoint())
                self._draw_start.setX(max(0.0, min(self._draw_start.x(), self._image_rect.right())))
                self._draw_start.setY(
                    max(0.0, min(self._draw_start.y(), self._image_rect.bottom()))
                )
                item = BBoxItem(
                    QRectF(self._draw_start, self._draw_start),
                    self._current_class,
                    class_color(self._current_class),
                    self._image_rect,
                )
                item.geometry_changed.connect(self.boxes_changed)
                self._scene.addItem(item)
                item.setSelected(True)
                self._drawing = item
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drawing is not None:
            current = self.mapToScene(event.position().toPoint())
            current.setX(max(self._image_rect.left(), min(current.x(), self._image_rect.right())))
            current.setY(max(self._image_rect.top(), min(current.y(), self._image_rect.bottom())))
            rect = QRectF(self._draw_start, current).normalized()
            self._drawing.set_rect(rect)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self._drawing is not None:
            rect = self._drawing.rect()
            if rect.width() < 5 or rect.height() < 5:
                self._scene.removeItem(self._drawing)
                self.selection_changed.emit(None)
            else:
                self.boxes_changed.emit()
                self.selection_changed.emit(self._drawing)
            self._drawing = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace) and self.delete_selected():
            event.accept()
            return
        super().keyPressEvent(event)
