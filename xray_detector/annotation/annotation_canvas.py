"""AnnotationCanvas – QGraphicsView för att rita och redigera rektanglar.

Interaktion:
- Dra med vänster musknapp på tom yta → ny rektangel
- Dra i en rektangel → flytta
- Dra i kant/hörn → ändra storlek (QGraphicsRectItem-standard)
- Markera + Delete → ta bort
- Varje rektangel har en klass (class_name) som visas som etikett
"""
from __future__ import annotations

import cv2
import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QImage,
    QPainter,
    QPen,
    QTransform,
)
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsScene, QGraphicsView


class RectItem(QGraphicsRectItem):
    """Rektangel med klassnamn och etikett."""

    def __init__(self, rect: QRectF, class_name: str = "", parent=None):
        super().__init__(rect, parent)
        self.class_name = class_name
        self.setFlags(
            QGraphicsRectItem.ItemIsMovable
            | QGraphicsRectItem.ItemIsSelectable
            | QGraphicsRectItem.ItemSendsGeometryChanges
        )
        self.setPen(QPen(QColor(0, 220, 0), 2))
        self.setBrush(QBrush(QColor(0, 220, 0, 40)))
        self._update_label()

    def _update_label(self) -> None:
        # Etiketten ritas i paint (se nedan)
        pass

    def paint(self, painter: QPainter, option, widget=None) -> None:
        super().paint(painter, option, widget)
        if not self.class_name:
            return
        # Rita etikett ovanför rektangeln
        rect = self.rect()
        font = QFont("Arial", 9)
        painter.setFont(font)
        text = self.class_name
        metrics = painter.fontMetrics()
        text_w = metrics.horizontalAdvance(text)
        text_h = metrics.height()
        label_x = rect.left()
        label_y = rect.top() - text_h - 2
        # Bakgrund
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 220, 0, 200))
        painter.drawRect(QRectF(label_x, label_y, text_w + 6, text_h + 2))
        # Text
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(QPointF(label_x + 3, label_y + text_h), text)


class AnnotationCanvas(QGraphicsView):
    """Vy över en fryst bild med ritbara rektanglar."""

    selection_changed = Signal(object)  # emitterar vald RectItem (eller None)

    def __init__(self, image: np.ndarray | None = None, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.NoDrag)
        self._image_item = None
        self._image: np.ndarray | None = None
        self._drawing = False
        self._start: QPointF | None = None
        self._rubber: QGraphicsRectItem | None = None
        self._scale = 1.0
        self.default_class = ""  # klass som nya rektanglar får
        self._scene.selectionChanged.connect(self._on_selection_changed)
        if image is not None:
            self.set_image(image)

    def _on_selection_changed(self) -> None:
        self.selection_changed.emit(self.selected_rect())

    # ---- Bild ----
    def set_image(self, image: np.ndarray | None) -> None:
        """Sätt bild, eller rensa vyn om ``image`` är ``None``."""
        self._image = image
        self._scene.clear()
        self._image_item = None
        if image is None:
            # Saknad videokälla – visa tydlig platshållare.
            self._scene.setSceneRect(QRectF(0, 0, 640, 480))
            text = self._scene.addText("Ingen videokälla")
            text.setDefaultTextColor(QColor(255, 107, 107))
            font = text.font()
            font.setPointSize(18)
            text.setFont(font)
            bounds = text.boundingRect()
            text.setPos(
                (640 - bounds.width()) / 2,
                (480 - bounds.height()) / 2,
            )
            self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)
            self._scale = self.transform().m11()
            return

        h, w = image.shape[:2]
        # BGR → RGB → QImage (hanterar både gråskala och färg)
        if image.ndim == 2:
            rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        else:
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb.data, w, h, w * 3, QImage.Format_RGB888).copy()
        self._image_item = self._scene.addPixmap(
            _qimage_to_pixmap(qimg)
        )
        self._scene.setSceneRect(QRectF(0, 0, w, h))
        self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)
        self._scale = self.transform().m11()

    @property
    def image(self) -> np.ndarray | None:
        return self._image

    def image_size(self) -> tuple[int, int]:
        if self._image is None:
            return (0, 0)
        h, w = self._image.shape[:2]
        return (w, h)

    # ---- Rektanglar ----
    def add_rect(self, x: float, y: float, w: float, h: float,
                 class_name: str | None = None) -> RectItem:
        """Lägg till en rektangel (i bild-pixlar).

        Om class_name inte anges används default_class.
        """
        if class_name is None:
            class_name = self.default_class
        item = RectItem(QRectF(x, y, w, h), class_name)
        self._scene.addItem(item)
        return item

    def rects(self) -> list[RectItem]:
        return [
            i for i in self._scene.items()
            if isinstance(i, RectItem)
        ]

    def clear_rects(self) -> None:
        for r in self.rects():
            self._scene.removeItem(r)

    def selected_rect(self) -> RectItem | None:
        items = self._scene.selectedItems()
        for i in items:
            if isinstance(i, RectItem):
                return i
        return None

    def delete_selected(self) -> None:
        r = self.selected_rect()
        if r is not None:
            self._scene.removeItem(r)

    def set_rect_class(self, rect: RectItem, class_name: str) -> None:
        rect.class_name = class_name
        rect.update()

    # ---- Mus: rita ny rektangel ----
    def mousePressEvent(self, event) -> None:
        if self._image is None:
            # Ingen bild – tillåt inte att rita rektanglar på tom yta.
            super().mousePressEvent(event)
            return
        if event.button() == Qt.LeftButton:
            pos = self.mapToScene(event.position().toPoint())
            # itemAt kräver en deviceTransform (identitet) i PySide6 – pos är
            # redan i scenkoordinater, så identitet är rätt transform.
            item_at_pos = self._scene.itemAt(pos, QTransform())
            # Om man klickar på tom yta (inte på en rektangel) → börja rita
            if item_at_pos is None or item_at_pos is self._image_item:
                self._drawing = True
                self._start = pos
                self._rubber = self._scene.addRect(
                    QRectF(pos, pos), QPen(QColor(255, 255, 0), 2, Qt.DashLine)
                )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drawing and self._start is not None and self._rubber is not None:
            pos = self.mapToScene(event.position().toPoint())
            rect = QRectF(self._start, pos).normalized()
            self._rubber.setRect(rect)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._drawing and self._start is not None:
            pos = self.mapToScene(event.position().toPoint())
            rect = QRectF(self._start, pos).normalized()
            if rect.width() > 3 and rect.height() > 3:
                # Ny rektangel får klassen som är vald i klasspanelen (sätts externt)
                self.add_rect(rect.left(), rect.top(), rect.width(), rect.height())
            if self._rubber is not None:
                self._scene.removeItem(self._rubber)
                self._rubber = None
            self._drawing = False
            self._start = None
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.delete_selected()
            event.accept()
            return
        super().keyPressEvent(event)


def _qimage_to_pixmap(qimg: QImage):
    from PySide6.QtGui import QPixmap
    return QPixmap.fromImage(qimg)
