from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from xray_detector.dataset.pending import PendingCapture, delete_pending_capture
from xray_detector.dataset.store import DatasetStore
from xray_detector.models import Detection
from xray_detector.ui.annotation_scene import AnnotationCanvas

LOGGER = logging.getLogger(__name__)


class AnnotationView(QWidget):
    saved = Signal(str)
    cancelled = Signal()

    def __init__(self, store: DatasetStore, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.store = store
        self.capture: PendingCapture | None = None
        self._loading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        header = QHBoxLayout()
        title = QLabel("Annotering")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        header.addWidget(title)

        header.addSpacing(16)
        header.addWidget(QLabel("Klass:"))
        self.class_combo = QComboBox()
        self.class_combo.setEditable(True)
        self.class_combo.setMinimumWidth(220)
        self.class_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.class_combo.currentTextChanged.connect(self._class_changed)
        header.addWidget(self.class_combo)

        delete_button = QPushButton("Ta bort vald")
        delete_button.clicked.connect(self._delete_selected)
        header.addWidget(delete_button)

        fit_button = QPushButton("Anpassa bild")
        fit_button.clicked.connect(self._fit_images)
        header.addWidget(fit_button)

        header.addStretch(1)
        self.status_label = QLabel("")
        header.addWidget(self.status_label)
        root.addLayout(header)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.canvases: dict[str, AnnotationCanvas] = {}
        self.title_labels: dict[str, QLabel] = {}
        root.addWidget(self.splitter, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel_button = QPushButton("Avbryt")
        cancel_button.clicked.connect(self._cancel)
        buttons.addWidget(cancel_button)
        self.save_button = QPushButton("Spara i dataset")
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(self._save)
        buttons.addWidget(self.save_button)
        root.addLayout(buttons)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def load_capture(self, capture: PendingCapture, classes: list[str]) -> None:
        self.capture = capture
        self._loading = True
        try:
            self.splitter.setUpdatesEnabled(False)
            while self.splitter.count():
                widget = self.splitter.widget(0)
                widget.setParent(None)
                widget.deleteLater()
            self.canvases.clear()
            self.title_labels.clear()

            cameras = list(capture.images)
            for camera in cameras:
                panel = QWidget()
                layout = QVBoxLayout(panel)
                layout.setContentsMargins(0, 0, 0, 0)
                label = QLabel("Vänster kamera" if camera == "left" else "Höger kamera")
                label.setStyleSheet("font-weight: 600;")
                layout.addWidget(label)
                canvas = AnnotationCanvas(camera)
                layout.addWidget(canvas, 1)
                self.splitter.addWidget(panel)
                self.canvases[camera] = canvas
                self.title_labels[camera] = label

            all_classes = sorted({item.strip() for item in classes if item.strip()})
            for image in capture.images.values():
                for detection in image.detections:
                    if detection.class_name.strip():
                        all_classes.append(detection.class_name.strip())
            with QSignalBlocker(self.class_combo):
                self.class_combo.clear()
                for name in dict.fromkeys(all_classes):
                    self.class_combo.addItem(name)
                if self.class_combo.count():
                    self.class_combo.setCurrentIndex(0)

            for camera, image in capture.images.items():
                canvas = self.canvases[camera]
                canvas.load_image(capture.image_path(camera))
                for detection in image.detections:
                    canvas.add_detection(detection)
            current = self.class_combo.currentText().strip()
            for canvas in self.canvases.values():
                canvas.set_current_class(current)
                canvas.set_draw_enabled(True)
            self.status_label.setText(
                f"{capture.group_id} · {len(capture.images)} bilder · "
                f"{sum(len(image.detections) for image in capture.images.values())} befintliga detektioner"
            )
        finally:
            self._loading = False
            self.splitter.setUpdatesEnabled(True)
            self.splitter.setSizes([1, 1])

    def _class_changed(self, text: str) -> None:
        if self._loading:
            return
        name = text.strip()
        for canvas in self.canvases.values():
            canvas.set_current_class(name)
        assigned = sum(canvas.assign_class(name) for canvas in self.canvases.values())
        if assigned:
            self.status_label.setText(f"Klass '{name}' tilldelad {assigned} box(ar)")

    def _delete_selected(self) -> None:
        for canvas in self.canvases.values():
            canvas.delete_selected()

    def _fit_images(self) -> None:
        for canvas in self.canvases.values():
            canvas.fit_image()

    def _collect(self) -> dict[str, list[Detection]]:
        result: dict[str, list[Detection]] = {}
        for camera, canvas in self.canvases.items():
            detections = []
            for detection in canvas.detections():
                name = detection.class_name.strip()
                if not name:
                    raise ValueError("Alla boxar maste ha en klass")
                detections.append(
                    Detection(
                        detection.x1,
                        detection.y1,
                        detection.x2,
                        detection.y2,
                        detection.class_id,
                        name,
                        detection.confidence,
                    )
                )
            result[camera] = detections
        return result

    def _save(self) -> None:
        if self.capture is None:
            return
        try:
            annotations = self._collect()
        except ValueError as exc:
            QMessageBox.warning(self, "Annotering", str(exc))
            return
        total = sum(len(items) for items in annotations.values())
        if total == 0:
            answer = QMessageBox.question(
                self,
                "Inga objekt",
                "Inga objekt är annoterade. Vill du spara bildparet som negativt exempel?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        try:
            images, objects = self.store.add_capture(self.capture, annotations)
        except Exception as exc:
            LOGGER.exception("Kunde inte spara annotering")
            QMessageBox.critical(self, "Kunde inte spara", str(exc))
            return
        delete_pending_capture(self.capture)
        message = (
            f"Bildparet sparades i dataset '{self.store.dataset_id}' "
            f"({images} bilder, {objects} annotationer)."
        )
        self._reset()
        self.saved.emit(message)

    def _cancel(self) -> None:
        if self.capture is None:
            return
        has_content = any(canvas.boxes() for canvas in self.canvases.values())
        if has_content:
            answer = QMessageBox.question(
                self,
                "Avbryt annotering",
                "Osparade annotationer finns. Vill du avbryta?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        delete_pending_capture(self.capture)
        self._reset()
        self.cancelled.emit()

    def _reset(self) -> None:
        self.capture = None
        self._loading = True
        self.class_combo.clear()
        self._loading = False
        for canvas in self.canvases.values():
            canvas.clear_boxes()
        self.status_label.clear()
