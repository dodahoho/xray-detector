import numpy as np
from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget

from xray_detector.application.background_task import BackgroundTask
from xray_detector.application.dataset_service import DatasetService
from xray_detector.domain.capture import StreamFrame
from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.ui.busy_indicator import BusyIndicator
from xray_detector.ui.colors import class_color
from xray_detector.ui.settings_dialog import settings_button
from xray_detector.ui.shortcuts import bind_shortcut, mnemonic, with_hint
from xray_detector.ui.style import ICON_BUTTON_WIDTH, button

HANDLE_SIZE = 8
MIN_SIZE = 8
ZOOM_MIN = 0.2
ZOOM_MAX = 5.0


class RectItem:
    def __init__(self, x1: float, y1: float, x2: float, y2: float, class_name: str) -> None:
        self.rect = QRect(
            int(min(x1, x2)),
            int(min(y1, y2)),
            int(abs(x2 - x1)),
            int(abs(y2 - y1)),
        )
        self.class_name = class_name


class AnnotationCanvas(QWidget):
    selection_changed = Signal(object)
    changed = Signal()

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
        self._zoom = 1.0
        self._pan = QPoint(0, 0)
        self._pan_start = QPoint()
        self.dirty = False
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

    def set_class_name(self, class_name: str) -> None:
        self.class_name = class_name
        if self.selected is not None:
            self.selected.class_name = class_name
            self._mark_dirty()
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
        self.dirty = False
        self._zoom = 1.0
        self._pan = QPoint(0, 0)
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

    def _base_scale(self) -> float:
        if self.image is None:
            return 1.0
        return min(
            self.width() / self.image.width(),
            self.height() / self.image.height(),
        )

    def _scale(self) -> float:
        return self._base_scale() * self._zoom

    def zoom_at(self, pos: QPoint, factor: float) -> None:
        """Zoomar kring muspositionen; bildpunkten under pekaren blir kvar."""
        if self.image is None:
            return
        image_point = self._to_image(pos - self._image_origin())
        new_zoom = max(ZOOM_MIN, min(ZOOM_MAX, self._zoom * factor))
        self._zoom = new_zoom
        scale = self._scale()
        desired_origin = pos - QPoint(int(image_point.x() * scale), int(image_point.y() * scale))
        self._pan = desired_origin - self._base_origin()

    def reset_view(self) -> None:
        self._zoom = 1.0
        self._pan = QPoint(0, 0)
        self.update()

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.25 if event.angleDelta().y() > 0 else 0.8
            self.zoom_at(event.position().toPoint(), factor)
            event.accept()
            return
        super().wheelEvent(event)

    def _to_widget(self, point: QPoint) -> QPoint:
        scale = self._scale()
        return QPoint(int(point.x() * scale), int(point.y() * scale))

    def _to_image(self, point: QPoint) -> QPoint:
        scale = self._scale()
        return QPoint(int(point.x() / scale), int(point.y() / scale))

    def _base_origin(self) -> QPoint:
        if self.image is None:
            return QPoint(0, 0)
        scale = self._base_scale()
        x = (self.width() - int(self.image.width() * scale)) // 2
        y = (self.height() - int(self.image.height() * scale)) // 2
        return QPoint(x, y)

    def _image_origin(self) -> QPoint:
        return self._base_origin() + self._pan

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
            pen.setColor(
                class_color(item.class_name) if item is not self.selected else QColor(255, 120, 0)
            )
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
        if event.button() == Qt.MouseButton.MiddleButton:
            self._mode = "pan"
            self._pan_start = pos
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
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
        if self._mode == "pan":
            self._pan += pos - self._pan_start
            self._pan_start = pos
            self.update()
            return
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
                self._mark_dirty()
                self.selection_changed.emit(item)
        if self._mode in ("move", "resize") and self.selected is not None:
            self._mark_dirty()
        if self._mode == "pan":
            self._mode = "idle"
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()
            return
        self._mode = "idle"
        self._drag_rect = None
        self.setCursor(self._hover_cursor(event.position().toPoint()))
        self.update()

    def _mark_dirty(self) -> None:
        if not self.dirty:
            self.dirty = True
            self.changed.emit()

    def delete_selected(self) -> None:
        if self.selected is not None:
            self.rects.remove(self.selected)
            self.selected = None
            self._mark_dirty()
            self.selection_changed.emit(None)
            self.update()


class AnnotationView(QWidget):
    saved = Signal()
    cancelled = Signal()

    def __init__(
        self, config, dataset: DatasetService, settings, model_classes=None, parent=None
    ) -> None:
        super().__init__(parent)
        self.config = config
        self.dataset_service = dataset
        self.settings = settings
        # anropbar som ger vald modells klassnamn; de är bara standardvärden (TASK-61)
        self.model_classes = model_classes
        self.pending_group_id: str | None = None
        # bilder som redan ligger i datasetet kräver en ändring före sparning (TASK-62)
        self._save_requires_change = False
        self._save_task: BackgroundTask | None = None
        layout = QVBoxLayout(self)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Klass:"))
        self.class_combo = QComboBox()
        self.class_combo.setEditable(True)
        self.class_combo.currentTextChanged.connect(self._on_class_changed)
        bar.addWidget(self.class_combo)
        self.add_class_button = button("+", width=ICON_BUTTON_WIDTH)
        self.add_class_button.setToolTip("Lägg till klassen som är angiven i rutan (Ctrl++)")
        self.add_class_button.clicked.connect(self._on_add_class)
        bar.addWidget(self.add_class_button)
        self.remove_class_button = button("−", width=ICON_BUTTON_WIDTH)
        self.remove_class_button.setToolTip("Ta bort den valda klassen ur listan (Ctrl+-)")
        self.remove_class_button.clicked.connect(self._on_remove_class)
        bar.addWidget(self.remove_class_button)
        self.delete_button = button(mnemonic("Ta bort markerad", "B"))
        self.delete_button.clicked.connect(self._on_delete)
        bar.addWidget(self.delete_button)
        bar.addStretch(1)
        self.save_button = button(mnemonic("Spara till dataset", "P"), primary=True)
        self.save_button.clicked.connect(self._on_save)
        bar.addWidget(self.save_button)
        self.cancel_button = button(with_hint("Avbryt", "Esc"))
        self.cancel_button.clicked.connect(self.cancelled.emit)
        bar.addWidget(self.cancel_button)
        self.settings_button = settings_button(self, "Inställningar – Annotation")
        bar.addWidget(self.settings_button)
        layout.addLayout(bar)
        panels = QHBoxLayout()
        self.canvases: list[AnnotationCanvas] = [AnnotationCanvas("Bild 1"), AnnotationCanvas("Bild 2")]
        for canvas in self.canvases:
            canvas.selection_changed.connect(self._on_selection_changed)
            canvas.changed.connect(self._update_save_button)
            panels.addWidget(canvas, 1)
        layout.addLayout(panels, 1)
        self.busy = BusyIndicator(self)
        bind_shortcut(self, "Esc", self.cancelled.emit)
        bind_shortcut(self, "Ctrl++", self._on_add_class)
        bind_shortcut(self, "Ctrl+-", self._on_remove_class)
        self.refresh_classes()

    def refresh_classes(self, seed_dataset: bool = False) -> None:
        """Bygger klasslistan ur datasetet; modellens klasser är standardvärden (TASK-61).

        Datasetet är master: listan är datasetets kategorier. Är datasetet tomt
        används vald modells klasser, och när vyn öppnas skrivs de in i
        datasetet så att de blir datasetets egna klasser.
        """
        names = self.dataset_service.classes()
        if not names and not self.dataset_service.has_dataset():
            names = self._default_classes()
            if seed_dataset and names:
                self.dataset_service.set_classes(names)
        current = self.class_combo.currentText()
        self.class_combo.blockSignals(True)
        self.class_combo.clear()
        self.class_combo.addItems(names)
        self.class_combo.blockSignals(False)
        index = self.class_combo.findText(current)
        if index < 0 and self.class_combo.count():
            index = 0
        self.class_combo.setCurrentIndex(index)
        self._on_class_changed(self.class_combo.currentText())

    def _default_classes(self) -> list[str]:
        """Standardklasserna: vald modells klasser, annars config.classes."""
        names = list(self.model_classes() if self.model_classes else [])
        return names or list(self.config.classes)

    def _class_names(self) -> list[str]:
        return [self.class_combo.itemText(i) for i in range(self.class_combo.count())]

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
        self.dataset_service.set_classes(self._class_names())

    def _on_remove_class(self) -> None:
        name = self.class_combo.currentText().strip()
        if not name:
            return
        if self.dataset_service.class_in_use(name):
            QMessageBox.information(
                self,
                "Ta bort klass",
                f'Klassen "{name}" används av sparade annoteringar och kan inte tas bort.',
            )
            return
        answer = QMessageBox.question(
            self,
            "Ta bort klass",
            f'Ta bort klassen "{name}" ur datasetets klasslista?',
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
        self.dataset_service.set_classes(self._class_names())

    def load_captures(
        self,
        captures: list,
        pending_group_id: str | None = None,
        already_saved: bool = False,
    ) -> None:
        """Laddar bilderna i vyn; already_saved kräver en ändring före sparning (TASK-62)."""
        self._save_requires_change = already_saved
        self.refresh_classes(seed_dataset=True)
        self.pending_group_id = pending_group_id
        for canvas in self.canvases:
            canvas.set_class_name(self.class_combo.currentText())
        for canvas, capture in zip(self.canvases, captures):
            canvas.load_frame(capture, self.class_combo.currentText())
        for canvas in self.canvases[len(captures):]:
            canvas.image = None
            canvas.rects = []
            canvas.selected = None
            canvas.update()
        self.mark_clean()

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

    def is_dirty(self) -> bool:
        return any(canvas.dirty for canvas in self.canvases)

    def mark_clean(self) -> None:
        for canvas in self.canvases:
            canvas.dirty = False
        self._update_save_button()

    def _update_save_button(self) -> None:
        """Spara-knappen är bara aktiv när det finns något att spara (TASK-62).

        Bilder som redan ligger i datasetet blir dubbletter om de sparas utan
        ändring, så där krävs en ändring först. En ny fångst finns inte i
        datasetet än och kan sparas direkt.
        """
        self.save_button.setEnabled(not self._save_requires_change or self.is_dirty())

    def _on_delete(self) -> None:
        for canvas in self.canvases:
            canvas.delete_selected()

    def _on_save(self) -> None:
        if self._save_task is not None:
            return
        samples = [canvas.result() for canvas in self.canvases if canvas.image is not None]
        samples = [sample for sample in samples if sample is not None]
        if not samples:
            return
        if not any(canvas.rects for canvas in self.canvases if canvas.image is not None):
            answer = QMessageBox.question(
                self,
                "Negativt exempel",
                "Inga objekt är markerade. Spara bilderna som negativa exempel (tomma annoteringar)?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        pending_group_id = self.pending_group_id
        # fångsttiden finns i pending-indexet, som skrevs vid knapptrycket
        captured = (
            self.dataset_service.pending_saved_at(pending_group_id)
            if pending_group_id
            else None
        )
        self.busy.start("Sparar annoteringar...")
        self.save_button.setEnabled(False)
        task = BackgroundTask(
            lambda: self._write(samples, captured, pending_group_id)
        )
        task.succeeded.connect(self._on_saved)
        task.failed.connect(self._on_save_failed)
        task.finished.connect(self._on_save_finished)
        self._save_task = task
        task.start()

    def _write(self, samples, captured, pending_group_id) -> None:
        """Skriver datasetet i arbetstråden, inklusive städning av pending (TASK-40)."""
        self.dataset_service.add_samples(samples, captured)
        if pending_group_id:
            self.dataset_service.remove_pending(pending_group_id)

    def _on_saved(self) -> None:
        self.pending_group_id = None
        self._save_requires_change = False
        self.mark_clean()
        for canvas in self.canvases:
            canvas.image = None
            canvas.rects = []
            canvas.reset_view()
            canvas.update()
        self.saved.emit()

    def _on_save_failed(self, message: str) -> None:
        QMessageBox.warning(
            self, "Kunde inte spara", f"Kunde inte spara annoteringarna: {message}"
        )

    def _on_save_finished(self) -> None:
        self._save_task = None
        self.busy.stop()
        self._update_save_button()

    def wait_for_save(self, timeout_ms: int = 10000) -> None:
        """Väntar in en pågående sparning (tester och stängning)."""
        if self._save_task is not None:
            self._save_task.wait(timeout_ms)
