import numpy as np
from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from xray_detector.capture.camera_service import StreamFrame
from xray_detector.dataset.store import AnnotatedImage, DatasetStore

HANDLE_SIZE = 8
MIN_SIZE = 8


class RectItem:
    def __init__(self, x1: float, y1: float, x2: float, y2: float, class_name: str) -> None:
        self.rect = QRect(
            int(min(x1, x2)),
            int(min(y1, y2)),
            int(abs(x2 - x1)),
            int(abs(y2 - y1)),
        )
        self.class_name = class_name
        self.color = QColor(255, 200, 60)


class AnnotationCanvas(QWidget):
    selection_changed = Signal(object)

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.title = title
        self.setMinimumSize(2, 2)
        self.image: QImage | None = None
        self.rects: list[RectItem] = []
        self.selected: RectItem | None = None
        self._drag_start = QPoint()
        self._drag_rect: QRect | None = None
        self._mode = "idle"
        self._handle = ""
        self._move_offset = QPoint()
        self.class_name = ""
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

    def set_class_name(self, class_name: str) -> None:
        self.class_name = class_name
        if self.selected is not None:
            self.selected.class_name = class_name
            self.update()

    def load_frame(self, stream_frame: StreamFrame, default_class: str) -> None:
        frame = stream_frame.frame
        height, width = frame.shape[:2]
        rgb = np.ascontiguousarray(frame[:, :, ::-1])
        self.image = QImage(
            rgb.data, width, height, 3 * width, QImage.Format.Format_RGB888
        ).copy()
        self.rects = [
            RectItem(
                d.x1, d.y1, d.x2, d.y2, d.class_name or default_class
            )
            for d in stream_frame.detections
        ]
        self.selected = None
        self.selection_changed.emit(None)
        self.update()

    def result(self) -> AnnotatedImage | None:
        if self.image is None:
            return None
        image = self.image.convertToFormat(QImage.Format.Format_RGB888)
        raw = np.frombuffer(image.constBits(), dtype=np.uint8)[: image.sizeInBytes()]
        stride = image.bytesPerLine()
        frame = raw[: image.height() * stride].reshape(image.height(), stride)
        frame = frame[:, : image.width() * 3].reshape(image.height(), image.width(), 3)
        frame = np.ascontiguousarray(frame[:, :, ::-1])
        annotations = [
            {
                "class_name": rect.class_name,
                "bbox": [rect.rect.x(), rect.rect.y(), rect.rect.width(), rect.rect.height()],
            }
            for rect in self.rects
        ]
        return AnnotatedImage(frame=frame, annotations=annotations)

    def _scale(self) -> float:
        if self.image is None:
            return 1.0
        return min(
            self.width() / self.image.width(),
            self.height() / self.image.height(),
        )

    def _to_widget(self, point: QPoint) -> QPoint:
        scale = self._scale()
        return QPoint(int(point.x() * scale), int(point.y() * scale))

    def _to_image(self, point: QPoint) -> QPoint:
        scale = self._scale()
        return QPoint(int(point.x() / scale), int(point.y() / scale))

    def _image_origin(self) -> QPoint:
        if self.image is None:
            return QPoint(0, 0)
        scale = self._scale()
        x = (self.width() - int(self.image.width() * scale)) // 2
        y = (self.height() - int(self.image.height() * scale)) // 2
        return QPoint(x, y)

    def _handle_points(self, rect: QRect) -> dict[str, QPoint]:
        top_left = self._to_widget(QPoint(rect.x(), rect.y())) + self._image_origin()
        bottom_right = self._to_widget(
            QPoint(rect.x() + rect.width(), rect.y() + rect.height())
        ) + self._image_origin()
        center = QPoint((top_left.x() + bottom_right.x()) // 2, (top_left.y() + bottom_right.y()) // 2)
        return {
            "top_left": top_left,
            "top_right": QPoint(bottom_right.x(), top_left.y()),
            "bottom_left": QPoint(top_left.x(), bottom_right.y()),
            "bottom_right": bottom_right,
            "top": QPoint((top_left.x() + bottom_right.x()) // 2, top_left.y()),
            "bottom": QPoint((top_left.x() + bottom_right.x()) // 2, bottom_right.y()),
            "left": QPoint(top_left.x(), (top_left.y() + bottom_right.y()) // 2),
            "right": QPoint(bottom_right.x(), (top_left.y() + bottom_right.y()) // 2),
            "_center": center,
        }

    def _hit_handle(self, pos: QPoint) -> str:
        if self.selected is None:
            return ""
        for name, point in self._handle_points(self.selected.rect).items():
            if name == "_center":
                continue
            if abs(pos.x() - point.x()) <= HANDLE_SIZE and abs(pos.y() - point.y()) <= HANDLE_SIZE:
                return name
        return ""

    def _hit_rect(self, pos: QPoint) -> RectItem | None:
        image_pos = self._to_image(pos - self._image_origin())
        for rect in reversed(self.rects):
            if rect.rect.contains(image_pos):
                return rect
        return None

    def _hover_cursor(self, pos: QPoint) -> Qt.CursorShape:
        handle = self._hit_handle(pos)
        if handle in {"top_left", "bottom_right"}:
            return Qt.CursorShape.SizeFDiagCursor
        if handle in {"top_right", "bottom_left"}:
            return Qt.CursorShape.SizeBDiagCursor
        if handle in {"left", "right"}:
            return Qt.CursorShape.SizeHorCursor
        if handle in {"top", "bottom"}:
            return Qt.CursorShape.SizeVerCursor
        if self._hit_rect(pos) is not None:
            return Qt.CursorShape.SizeAllCursor
        return Qt.CursorShape.ArrowCursor

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(30, 30, 30))
        if self.image is None:
            painter.setPen(QColor(150, 150, 150))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Ingen bild")
            return
        origin = self._image_origin()
        scale = self._scale()
        size = self.image.size() * scale
        painter.drawImage(QRect(origin, size), self.image)
        pen = QPen()
        pen.setWidth(4)
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        painter.setFont(font)
        for item in self.rects:
            pen.setColor(item.color if item is not self.selected else QColor(255, 120, 0))
            painter.setPen(pen)
            top_left = self._to_widget(QPoint(item.rect.x(), item.rect.y())) + origin
            bottom_right = self._to_widget(
                QPoint(
                    item.rect.x() + item.rect.width(),
                    item.rect.y() + item.rect.height(),
                )
            ) + origin
            painter.drawRect(QRect(top_left, bottom_right))
            painter.drawText(top_left.x(), max(22, top_left.y() - 8), item.class_name)
            if item is self.selected:
                brush_pen = QPen(QColor(255, 120, 0))
                brush_pen.setWidth(2)
                painter.setPen(brush_pen)
                for point in self._handle_points(item.rect).values():
                    painter.drawRect(
                        int(point.x()) - HANDLE_SIZE // 2,
                        int(point.y()) - HANDLE_SIZE // 2,
                        HANDLE_SIZE,
                        HANDLE_SIZE,
                    )
        if self._drag_rect is not None and self._mode == "draw":
            preview_pen = QPen(QColor(255, 200, 60))
            preview_pen.setWidth(4)
            painter.setPen(preview_pen)
            painter.drawRect(self._drag_rect)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            if self.selected is not None:
                self.delete_selected()
                event.accept()
                return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.image is None:
            return
        pos = event.position().toPoint()
        handle = self._hit_handle(pos)
        if handle:
            self._mode = "resize"
            self._handle = handle
            self._drag_start = pos
            self.setCursor(self._hover_cursor(pos))
            self.setFocus(Qt.FocusReason.MouseFocusReason)
            return
        hit = self._hit_rect(pos)
        if hit is not None:
            self.selected = hit
            self._mode = "move"
            self.setCursor(self._hover_cursor(pos))
            self.setFocus(Qt.FocusReason.MouseFocusReason)
            image_pos = self._to_image(pos - self._image_origin())
            self._move_offset = image_pos - QPoint(hit.rect.x(), hit.rect.y())
            self.selection_changed.emit(hit)
            self.update()
            return
        self.selected = None
        self.selection_changed.emit(None)
        if event.button() == Qt.MouseButton.LeftButton:
            self._mode = "draw"
            self._drag_start = pos
            self._drag_rect = QRect(pos, pos)
            self.setCursor(Qt.CursorShape.CrossCursor)
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.image is None:
            return
        pos = event.position().toPoint()
        if self._mode == "idle":
            self.setCursor(self._hover_cursor(pos))
            return
        if self._mode == "draw":
            self._drag_rect = QRect(self._drag_start, pos).normalized()
            self.update()
        elif self._mode == "move" and self.selected is not None:
            image_pos = self._to_image(pos - self._image_origin())
            new_top_left = image_pos - self._move_offset
            new_top_left.setX(max(0, min(new_top_left.x(), self.image.width() - self.selected.rect.width())))
            new_top_left.setY(max(0, min(new_top_left.y(), self.image.height() - self.selected.rect.height())))
            self.selected.rect.moveTo(new_top_left)
            self.update()
        elif self._mode == "resize" and self.selected is not None:
            image_pos = self._to_image(pos - self._image_origin())
            rect = self.selected.rect
            if "left" in self._handle:
                rect.setLeft(min(image_pos.x(), rect.right() - MIN_SIZE))
            if "right" in self._handle:
                rect.setRight(max(image_pos.x(), rect.left() + MIN_SIZE))
            if "top" in self._handle:
                rect.setTop(min(image_pos.y(), rect.bottom() - MIN_SIZE))
            if "bottom" in self._handle:
                rect.setBottom(max(image_pos.y(), rect.top() + MIN_SIZE))
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._mode == "draw" and self._drag_rect is not None and self.image is not None:
            if self._drag_rect.width() >= 4 and self._drag_rect.height() >= 4:
                top_left = self._to_image(self._drag_rect.topLeft() - self._image_origin())
                bottom_right = self._to_image(self._drag_rect.bottomRight() - self._image_origin())
                item = RectItem(
                    top_left.x(),
                    top_left.y(),
                    bottom_right.x(),
                    bottom_right.y(),
                    self.class_name or "objekt",
                )
                self.rects.append(item)
                self.selected = item
                self.selection_changed.emit(item)
        self._mode = "idle"
        self._drag_rect = None
        self.setCursor(self._hover_cursor(event.position().toPoint()))
        self.update()

    def delete_selected(self) -> None:
        if self.selected is not None:
            self.rects.remove(self.selected)
            self.selected = None
            self.selection_changed.emit(None)
            self.update()


class AnnotationView(QWidget):
    saved = Signal()
    cancelled = Signal()

    def __init__(self, config, store: DatasetStore, settings, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.store = store
        self.settings = settings
        layout = QVBoxLayout(self)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Klass:"))
        self.class_combo = QComboBox()
        self.class_combo.setEditable(True)
        stored_classes = self.settings.value("annotation/classes")
        if isinstance(stored_classes, (list, tuple)) and stored_classes:
            self.class_combo.addItems([str(name) for name in stored_classes])
        else:
            self.class_combo.addItems(config.classes)
        self.class_combo.currentTextChanged.connect(self._on_class_changed)
        bar.addWidget(self.class_combo)
        self.add_class_button = QPushButton("+")
        self.add_class_button.setFixedWidth(36)
        self.add_class_button.setToolTip("Lägg till klassen som är angiven i rutan")
        self.add_class_button.clicked.connect(self._on_add_class)
        bar.addWidget(self.add_class_button)
        self.remove_class_button = QPushButton("−")
        self.remove_class_button.setFixedWidth(36)
        self.remove_class_button.setToolTip("Ta bort den valda klassen ur listan")
        self.remove_class_button.clicked.connect(self._on_remove_class)
        bar.addWidget(self.remove_class_button)
        self.delete_button = QPushButton("Ta bort markerad")
        self.delete_button.clicked.connect(self._on_delete)
        bar.addWidget(self.delete_button)
        bar.addStretch(1)
        self.save_button = QPushButton("Spara till dataset")
        self.save_button.setMinimumHeight(40)
        self.save_button.clicked.connect(self._on_save)
        bar.addWidget(self.save_button)
        self.cancel_button = QPushButton("Avbryt")
        self.cancel_button.clicked.connect(self.cancelled.emit)
        bar.addWidget(self.cancel_button)
        layout.addLayout(bar)
        panels = QHBoxLayout()
        self.canvases: list[AnnotationCanvas] = [AnnotationCanvas("Bild 1"), AnnotationCanvas("Bild 2")]
        for canvas in self.canvases:
            canvas.selection_changed.connect(self._on_selection_changed)
            panels.addWidget(canvas, 1)
        layout.addLayout(panels, 1)

    def restore_settings(self) -> None:
        class_name = self.settings.value("annotation/class", type=str)
        if class_name:
            index = self.class_combo.findText(class_name)
            if index >= 0:
                self.class_combo.setCurrentIndex(index)
            else:
                self.class_combo.setEditText(class_name)
                self._on_class_changed(class_name)

    def save_settings(self) -> None:
        self.settings.setValue("annotation/class", self.class_combo.currentText())
        self.settings.setValue(
            "annotation/classes",
            [self.class_combo.itemText(i) for i in range(self.class_combo.count())],
        )

    def _on_add_class(self) -> None:
        name = self.class_combo.currentText().strip()
        if not name:
            QMessageBox.information(self, "Lägg till klass", "Skriv ett namn på klassen först.")
            return
        index = self.class_combo.findText(name)
        if index < 0:
            self.class_combo.addItem(name)
            index = self.class_combo.findText(name)
        self.class_combo.setCurrentIndex(index)
        self.save_settings()

    def _on_remove_class(self) -> None:
        name = self.class_combo.currentText().strip()
        if not name:
            return
        answer = QMessageBox.question(
            self,
            "Ta bort klass",
            f"Ta bort klassen \"{name}\" ur listan? Sparade annoteringar påverkas inte.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        index = self.class_combo.findText(name)
        if index >= 0:
            self.class_combo.removeItem(index)
        if self.class_combo.count() == 0:
            self.class_combo.setCurrentIndex(-1)
            self._on_class_changed("")
        else:
            self.class_combo.setCurrentIndex(0)
        self.save_settings()

    def load_captures(self, captures: list) -> None:
        for canvas in self.canvases:
            canvas.set_class_name(self.class_combo.currentText())
        for canvas, capture in zip(self.canvases, captures):
            canvas.load_frame(capture, self.class_combo.currentText())
        for canvas in self.canvases[len(captures):]:
            canvas.image = None
            canvas.rects = []
            canvas.selected = None
            canvas.update()

    def _on_class_changed(self, class_name: str) -> None:
        for canvas in self.canvases:
            canvas.set_class_name(class_name)

    def _on_selection_changed(self, item) -> None:
        if item is not None:
            index = self.class_combo.findText(item.class_name)
            if index >= 0:
                self.class_combo.setCurrentIndex(index)
            else:
                self.class_combo.setEditText(item.class_name)

    def _on_delete(self) -> None:
        for canvas in self.canvases:
            canvas.delete_selected()

    def _on_save(self) -> None:
        samples = [canvas.result() for canvas in self.canvases if canvas.image is not None]
        samples = [sample for sample in samples if sample is not None]
        if not samples:
            return
        version = self.store.current_version() or self.store.new_version()
        self.store.add_samples(version, samples)
        for canvas in self.canvases:
            canvas.image = None
            canvas.rects = []
            canvas.update()
        self.saved.emit()
