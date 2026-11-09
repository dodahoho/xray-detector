"""Prototyp (spike, TASK-21): annotering pa QGraphicsScene/QGraphicsView.

Detta ar INTE produktionskod utan en utvarderingsprototyp som visar hur
annoteringsduken kan se ut pa QGraphics-scenografi:

- BoxItem (QGraphicsRectItem) med 8 storleksandring-handtag, mamdj
  grans (MIN_BOX) och kosmetisk penna (pen.setCosmetic(True)) sa att
  linjetjocklecken ar konstant pa skermen oavsett zoomniva.
- AnnotationScene med bildunderlag och raster for boxar.
- AnnotationView med Ctrl+musjul-zoom och panorering med mittenknappen
  (inbyggt i QGraphicsView-grunden).

Kors av tests/test_prototype_annotation_scene.py.
"""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
)

HANDLE_SIZE = 8.0
MIN_BOX = 4.0
NORMAL_COLOR = QColor(255, 200, 60)
SELECTED_COLOR = QColor(255, 120, 0)


class BoxItem(QGraphicsRectItem):
    """Markeringsrektangel med resize-handtag och kosmetisk penna."""

    def __init__(self, rect: QRectF, class_name: str, view=None) -> None:
        super().__init__(rect)
        self.class_name = class_name
        self._view = view
        self.setFlags(
            QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setZValue(10.0)
        self.setAcceptHoverEvents(True)
        self._apply_style()

    # ---stil---

    def _apply_style(self) -> None:
        color = SELECTED_COLOR if self.isSelected() else NORMAL_COLOR
        pen = QPen(color, 2.0)
        pen.setCosmetic(True)  # konstant skarm-tjocklek oavsett zoom
        self.setPen(pen)
        self.setBrush(QBrush(QColor(color.red(), color.green(), color.blue(), 30)))

    def itemChange(self, change, value):
        if change == QGraphicsRectItem.GraphicsItemChange.ItemSelectedChange:
            self._apply_style()
        return super().itemChange(change, value)

    # ---handtag for storleksandring---

    def _scale(self) -> float:
        if self._view is not None:
            scale = self._view.transform().m11()
            if scale > 0:
                return scale
        return 1.0

    def handle_rects(self) -> dict[str, QRectF]:
        size = HANDLE_SIZE / self._scale()
        rect = self.rect()
        corners = {
            "tl": rect.topLeft(),
            "tr": rect.topRight(),
            "bl": rect.bottomLeft(),
            "br": rect.bottomRight(),
            "t": QPointF(rect.center().x(), rect.top()),
            "b": QPointF(rect.center().x(), rect.bottom()),
            "l": QPointF(rect.left(), rect.center().y()),
            "r": QPointF(rect.right(), rect.center().y()),
        }
        return {
            name: QRectF(point.x() - size / 2, point.y() - size / 2, size, size)
            for name, point in corners.items()
        }

    def hit_handle(self, pos: QPointF) -> str:
        for name, area in self.handle_rects().items():
            if area.contains(pos):
                return name
        return ""

    def resize_to(self, handle: str, pos: QPointF) -> None:
        """Storleksandra sa att handtaget hamnar pa pos (bildkoordinater)."""
        rect = self.rect()
        if "l" in handle:
            rect.setLeft(min(pos.x(), rect.right() - MIN_BOX))
        if "r" in handle:
            rect.setRight(max(pos.x(), rect.left() + MIN_BOX))
        if "t" in handle:
            rect.setTop(min(pos.y(), rect.bottom() - MIN_BOX))
        if "b" in handle:
            rect.setBottom(max(pos.y(), rect.top() + MIN_BOX))
        self.setRect(rect.normalized())


class AnnotationScene(QGraphicsScene):
    def __init__(self) -> None:
        super().__init__()
        self.backdrop: QGraphicsPixmapItem | None = None
        self.boxes: list[BoxItem] = []

    def set_background(self, pixmap) -> None:
        if self.backdrop is not None:
            self.removeItem(self.backdrop)
        self.backdrop = self.addPixmap(pixmap)
        self.backdrop.setZValue(0.0)

    def add_box(self, rect: QRectF, class_name: str, view=None) -> BoxItem:
        box = BoxItem(rect, class_name, view)
        self.addItem(box)
        self.boxes.append(box)
        return box

    def boxes_as_annotations(self) -> list[dict]:
        out = []
        for box in self.boxes:
            rect = box.rect()
            out.append(
                {
                    "class_name": box.class_name,
                    "bbox": [rect.x(), rect.y(), rect.width(), rect.height()],
                }
            )
        return out


class AnnotationView(QGraphicsView):
    """Ctrl+musjul zoomar, mittenknappen panorerar (QGraphicsView-inbyggt)."""

    def __init__(self, scene: AnnotationScene, parent=None) -> None:
        super().__init__(scene, parent)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setRenderHints(self.renderHints())

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.25 if event.angleDelta().y() > 0 else 0.8
            self.scale(factor, factor)
            event.accept()
            return
        super().wheelEvent(event)
