from __future__ import annotations

from typing import List, Optional
import cv2
import numpy as np
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QImage,
    QPainter,
    QPen,
    QBrush,
    QPixmap,
    QKeyEvent,
    QMouseEvent,
)
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSceneHoverEvent,
    QGraphicsSceneMouseEvent,
    QGraphicsView,
)

from src.core.models_schema import BoundingBox


CLASS_COLORS = [
    QColor(0, 210, 255),
    QColor(46, 213, 115),
    QColor(255, 165, 2),
    QColor(255, 71, 87),
    QColor(165, 94, 234),
    QColor(255, 107, 129),
    QColor(30, 144, 255),
]


def color_for_class(class_name: str) -> QColor:
    idx = sum(ord(c) for c in class_name) % len(CLASS_COLORS)
    return CLASS_COLORS[idx]


class EditableBoxItem(QGraphicsRectItem):
    """Interaktiv rektangel (BoundingBox) som kan storleksändras via alla 4 hörn och 4 kanter samt flyttas."""

    HANDLE_NONE = 0
    HANDLE_TOP_LEFT = 1
    HANDLE_TOP = 2
    HANDLE_TOP_RIGHT = 3
    HANDLE_RIGHT = 4
    HANDLE_BOTTOM_RIGHT = 5
    HANDLE_BOTTOM = 6
    HANDLE_BOTTOM_LEFT = 7
    HANDLE_LEFT = 8
    HANDLE_MOVE = 9

    HANDLE_MARGIN = 10.0  # Greppzon i pixlar för kant och hörn
    MIN_SIZE = 12.0

    def __init__(
        self,
        box: BoundingBox,
        img_width: int,
        img_height: int,
        on_selected_callback=None,
        on_changed_callback=None,
    ) -> None:
        b = box.normalized()
        super().__init__(QRectF(b.x1, b.y1, max(self.MIN_SIZE, b.width), max(self.MIN_SIZE, b.height)))
        self.box_id = b.box_id
        self.class_name = b.class_name
        self.confidence = b.confidence
        self.is_manual = b.is_manual
        self.img_width = float(img_width)
        self.img_height = float(img_height)
        self.on_selected_callback = on_selected_callback
        self.on_changed_callback = on_changed_callback

        self._active_handle = self.HANDLE_NONE
        self._drag_start_pos = QPointF()
        self._drag_start_rect = QRectF()

        self.setAcceptHoverEvents(True)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setZValue(10.0)

    def to_bounding_box(self) -> BoundingBox:
        r = self.rect().normalized()
        return BoundingBox(
            x1=float(r.left()),
            y1=float(r.top()),
            x2=float(r.right()),
            y2=float(r.bottom()),
            class_name=self.class_name,
            confidence=self.confidence,
            is_manual=self.is_manual,
            box_id=self.box_id,
        )

    def set_class_name(self, new_class: str) -> None:
        self.class_name = new_class
        self.update()
        if self.on_changed_callback:
            self.on_changed_callback(self)

    def _hit_test_handle(self, pos: QPointF) -> int:
        r = self.rect()
        m = self.HANDLE_MARGIN

        near_left = abs(pos.x() - r.left()) <= m
        near_right = abs(pos.x() - r.right()) <= m
        near_top = abs(pos.y() - r.top()) <= m
        near_bottom = abs(pos.y() - r.bottom()) <= m

        in_x = (r.left() - m) <= pos.x() <= (r.right() + m)
        in_y = (r.top() - m) <= pos.y() <= (r.bottom() + m)

        if near_left and near_top:
            return self.HANDLE_TOP_LEFT
        if near_right and near_top:
            return self.HANDLE_TOP_RIGHT
        if near_right and near_bottom:
            return self.HANDLE_BOTTOM_RIGHT
        if near_left and near_bottom:
            return self.HANDLE_BOTTOM_LEFT
        if near_top and in_x:
            return self.HANDLE_TOP
        if near_bottom and in_x:
            return self.HANDLE_BOTTOM
        if near_left and in_y:
            return self.HANDLE_LEFT
        if near_right and in_y:
            return self.HANDLE_RIGHT
        if r.contains(pos):
            return self.HANDLE_MOVE
        return self.HANDLE_NONE

    def _cursor_for_handle(self, handle: int) -> Qt.CursorShape:
        if handle in (self.HANDLE_TOP_LEFT, self.HANDLE_BOTTOM_RIGHT):
            return Qt.CursorShape.SizeFDiagCursor
        if handle in (self.HANDLE_TOP_RIGHT, self.HANDLE_BOTTOM_LEFT):
            return Qt.CursorShape.SizeBDiagCursor
        if handle in (self.HANDLE_TOP, self.HANDLE_BOTTOM):
            return Qt.CursorShape.SizeVerCursor
        if handle in (self.HANDLE_LEFT, self.HANDLE_RIGHT):
            return Qt.CursorShape.SizeHorCursor
        if handle == self.HANDLE_MOVE:
            return Qt.CursorShape.SizeAllCursor
        return Qt.CursorShape.ArrowCursor

    def boundingRect(self) -> QRectF:
        # Inkludera marginal för handtag och etikett ovanför rektangeln
        r = self.rect().normalized()
        return r.adjusted(-12, -28, 12, 12)

    def hoverMoveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        handle = self._hit_test_handle(event.pos())
        self.setCursor(QCursor(self._cursor_for_handle(handle)))
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.setSelected(True)
            if self.on_selected_callback:
                self.on_selected_callback(self)
            self._active_handle = self._hit_test_handle(event.pos())
            self._drag_start_pos = event.pos()
            self._drag_start_rect = QRectF(self.rect())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._active_handle == self.HANDLE_NONE:
            super().mouseMoveEvent(event)
            return

        delta = event.pos() - self._drag_start_pos
        r = QRectF(self._drag_start_rect)

        left, top, right, bottom = r.left(), r.top(), r.right(), r.bottom()

        if self._active_handle == self.HANDLE_MOVE:
            w, h = r.width(), r.height()
            new_left = max(0.0, min(self.img_width - w, left + delta.x()))
            new_top = max(0.0, min(self.img_height - h, top + delta.y()))
            self.prepareGeometryChange()
            self.setRect(QRectF(new_left, new_top, w, h))
        else:
            if self._active_handle in (
                self.HANDLE_TOP_LEFT,
                self.HANDLE_LEFT,
                self.HANDLE_BOTTOM_LEFT,
            ):
                left = max(0.0, min(right - self.MIN_SIZE, left + delta.x()))
            if self._active_handle in (
                self.HANDLE_TOP_RIGHT,
                self.HANDLE_RIGHT,
                self.HANDLE_BOTTOM_RIGHT,
            ):
                right = min(self.img_width, max(left + self.MIN_SIZE, right + delta.x()))
            if self._active_handle in (
                self.HANDLE_TOP_LEFT,
                self.HANDLE_TOP,
                self.HANDLE_TOP_RIGHT,
            ):
                top = max(0.0, min(bottom - self.MIN_SIZE, top + delta.y()))
            if self._active_handle in (
                self.HANDLE_BOTTOM_LEFT,
                self.HANDLE_BOTTOM,
                self.HANDLE_BOTTOM_RIGHT,
            ):
                bottom = min(self.img_height, max(top + self.MIN_SIZE, bottom + delta.y()))

            self.prepareGeometryChange()
            self.setRect(QRectF(QPointF(left, top), QPointF(right, bottom)).normalized())

        if self.on_changed_callback:
            self.on_changed_callback(self)
        event.accept()

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self._active_handle = self.HANDLE_NONE
        if self.on_changed_callback:
            self.on_changed_callback(self)
        super().mouseReleaseEvent(event)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        r = self.rect().normalized()
        base_color = color_for_class(self.class_name)
        is_sel = self.isSelected()

        # Ram och fyllning
        pen_width = 3.0 if is_sel else 2.0
        border_color = QColor(255, 255, 255) if is_sel else base_color
        painter.setPen(QPen(border_color, pen_width))

        fill_color = QColor(base_color)
        fill_color.setAlpha(55 if is_sel else 30)
        painter.setBrush(QBrush(fill_color))
        painter.drawRect(r)

        # Rita 8 tydliga greppunkter (hörn + kanter) så att användaren ser var man drar
        handle_size = 7.0 if is_sel else 5.0
        painter.setPen(QPen(QColor(20, 25, 30), 1.5))
        painter.setBrush(QBrush(QColor(255, 255, 255) if is_sel else base_color))

        cx = r.center().x()
        cy = r.center().y()
        handle_centers = [
            QPointF(r.left(), r.top()),
            QPointF(cx, r.top()),
            QPointF(r.right(), r.top()),
            QPointF(r.right(), cy),
            QPointF(r.right(), r.bottom()),
            QPointF(cx, r.bottom()),
            QPointF(r.left(), r.bottom()),
            QPointF(r.left(), cy),
        ]
        for pt in handle_centers:
            painter.drawRect(
                QRectF(
                    pt.x() - handle_size / 2.0,
                    pt.y() - handle_size / 2.0,
                    handle_size,
                    handle_size,
                )
            )

        # Klassetikett ovanför rektangeln
        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(font)
        conf_str = "" if self.is_manual else f" ({int(self.confidence * 100)}%)"
        label_text = f" {self.class_name}{conf_str} "
        fm = painter.fontMetrics()
        tw = fm.horizontalAdvance(label_text) + 8
        th = fm.height() + 4

        label_y = r.top() - th if r.top() >= th else r.top()
        label_rect = QRectF(r.left(), label_y, tw, th)
        painter.setPen(Qt.PenStyle.NoPen)
        tag_bg = QColor(base_color)
        tag_bg.setAlpha(230)
        painter.setBrush(QBrush(tag_bg))
        painter.drawRoundedRect(label_rect, 3.0, 3.0)

        painter.setPen(QColor(10, 12, 16))
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, label_text)


class AnnotationCanvas(QGraphicsView):
    """Interaktiv bildunderlagsvy för en av de två frysta röntgenbilderna.

    Stöder:
    - Automatisk inritning av befintliga detektioner från detektionsläget
    - Nyritning av rektanglar genom att klicka och dra på bilden
    - Storleksändring av samtliga rektanglar via hörn eller kant
    - Klassbyte och borttagning av markerad rektangel
    """

    box_selected = Signal(object)  # EditableBoxItem | None
    boxes_changed = Signal()

    def __init__(self, stream_id: int, title: str, parent=None) -> None:
        super().__init__(parent)
        self.stream_id = stream_id
        self.title = title
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setStyleSheet("background-color: #11161d; border: 1px solid #2c3545; border-radius: 6px;")
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        self._img_width: int = 1280
        self._img_height: int = 720
        self._current_class: str = "Metallföremål"

        self._drawing_new: bool = False
        self._draw_start_scene_pos = QPointF()
        self._preview_rect_item: Optional[QGraphicsRectItem] = None

    def set_active_class_for_new_boxes(self, class_name: str) -> None:
        if class_name.strip():
            self._current_class = class_name.strip()

    def load_frozen_frame(self, frame_bgr: np.ndarray, initial_boxes: List[BoundingBox]) -> None:
        """Laddar in fryst bild och ritar automatiskt in befintliga detektioner som redigerbara rektanglar."""
        self._scene.clear()
        self._pixmap_item = None
        self._preview_rect_item = None

        if frame_bgr is None or frame_bgr.size == 0:
            return

        h, w = frame_bgr.shape[:2]
        self._img_width = w
        self._img_height = h

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb.data, w, h, rgb.strides[0], QImage.Format.Format_RGB888).copy()
        pixmap = QPixmap.fromImage(qimg)

        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._pixmap_item.setZValue(0.0)
        self._scene.setSceneRect(0, 0, w, h)

        for box in initial_boxes:
            self._add_box_item(box)

        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.boxes_changed.emit()

    def _add_box_item(self, box: BoundingBox, select: bool = False) -> EditableBoxItem:
        item = EditableBoxItem(
            box=box,
            img_width=self._img_width,
            img_height=self._img_height,
            on_selected_callback=self._on_item_selected,
            on_changed_callback=lambda _: self.boxes_changed.emit(),
        )
        self._scene.addItem(item)
        if select:
            for existing in self.get_box_items():
                existing.setSelected(existing is item)
            self.box_selected.emit(item)
        return item

    def _on_item_selected(self, item: EditableBoxItem) -> None:
        for existing in self.get_box_items():
            if existing is not item and existing.isSelected():
                existing.setSelected(False)
        self.box_selected.emit(item)

    def get_box_items(self) -> List[EditableBoxItem]:
        return [i for i in self._scene.items() if isinstance(i, EditableBoxItem)]

    def get_selected_box_item(self) -> Optional[EditableBoxItem]:
        for item in self.get_box_items():
            if item.isSelected():
                return item
        return None

    def get_boxes(self) -> List[BoundingBox]:
        return [item.to_bounding_box() for item in self.get_box_items()]

    def delete_selected_box(self) -> bool:
        sel = self.get_selected_box_item()
        if sel is not None:
            self._scene.removeItem(sel)
            self.box_selected.emit(None)
            self.boxes_changed.emit()
            return True
        return False

    def clear_selection(self) -> None:
        for item in self.get_box_items():
            item.setSelected(False)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._scene.sceneRect().width() > 0:
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            if self.delete_selected_box():
                event.accept()
                return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            # Kontrollera om klicket träffar en befintlig EditableBoxItem (inklusive dess kant/hörn)
            for item in self.get_box_items():
                local_pos = item.mapFromScene(scene_pos)
                if item._hit_test_handle(local_pos) != EditableBoxItem.HANDLE_NONE:
                    super().mousePressEvent(event)
                    return

            # Om klicket är på fri bildyta -> påbörja ny rektangel!
            if 0 <= scene_pos.x() <= self._img_width and 0 <= scene_pos.y() <= self._img_height:
                self.clear_selection()
                self.box_selected.emit(None)
                self._drawing_new = True
                self._draw_start_scene_pos = scene_pos
                self._preview_rect_item = QGraphicsRectItem(QRectF(scene_pos, scene_pos))
                c = color_for_class(self._current_class)
                self._preview_rect_item.setPen(QPen(c, 2.5, Qt.PenStyle.DashLine))
                fill = QColor(c)
                fill.setAlpha(45)
                self._preview_rect_item.setBrush(QBrush(fill))
                self._preview_rect_item.setZValue(20.0)
                self._scene.addItem(self._preview_rect_item)
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drawing_new and self._preview_rect_item is not None:
            scene_pos = self.mapToScene(event.pos())
            clamped_x = max(0.0, min(float(self._img_width), scene_pos.x()))
            clamped_y = max(0.0, min(float(self._img_height), scene_pos.y()))
            rect = QRectF(self._draw_start_scene_pos, QPointF(clamped_x, clamped_y)).normalized()
            self._preview_rect_item.setRect(rect)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._drawing_new:
            self._drawing_new = False
            if self._preview_rect_item is not None:
                rect = self._preview_rect_item.rect().normalized()
                self._scene.removeItem(self._preview_rect_item)
                self._preview_rect_item = None

                if rect.width() >= 12.0 and rect.height() >= 12.0:
                    new_box = BoundingBox(
                        x1=float(rect.left()),
                        y1=float(rect.top()),
                        x2=float(rect.right()),
                        y2=float(rect.bottom()),
                        class_name=self._current_class,
                        confidence=1.0,
                        is_manual=True,
                    )
                    self._add_box_item(new_box, select=True)
                    self.boxes_changed.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)
