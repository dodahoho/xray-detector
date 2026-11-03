"""Annotation mode for a captured image pair."""

from __future__ import annotations

from PySide6.QtCore import Signal
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

from xray_detector.application.dataset_service import DatasetService
from xray_detector.config import AppConfig
from xray_detector.domain.annotation import AnnotationBox
from xray_detector.domain.detection import CaptureSnapshot
from xray_detector.ui.widgets.annotation_canvas import AnnotationCanvas
from xray_detector.ui.widgets.video_panel import class_color


class AnnotationView(QWidget):
    saved = Signal(object)
    cancelled = Signal()

    def __init__(
        self,
        snapshot: CaptureSnapshot,
        config: AppConfig,
        dataset_service: DatasetService,
        class_names: list[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.snapshot = snapshot
        self.config = config
        self.dataset_service = dataset_service
        self._active_canvas: AnnotationCanvas | None = None
        self._updating_combo = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        top = QHBoxLayout()
        top.addWidget(QLabel(f"Bildpar: {snapshot.pair_id}"))
        top.addSpacing(16)
        top.addWidget(QLabel("Klass:"))
        self.class_combo = QComboBox()
        self.class_combo.setEditable(True)
        self.class_combo.setMinimumWidth(220)
        top.addWidget(self.class_combo)
        self.apply_button = QPushButton("Använd klass")
        self.apply_button.clicked.connect(self.apply_class)
        top.addWidget(self.apply_button)
        self.delete_button = QPushButton("Ta bort box")
        self.delete_button.clicked.connect(self.delete_selected)
        top.addWidget(self.delete_button)
        self.fit_button = QPushButton("Anpassa vy")
        self.fit_button.clicked.connect(self.fit_views)
        top.addWidget(self.fit_button)
        top.addStretch(1)
        self.save_button = QPushButton("Spara till dataset")
        self.save_button.setStyleSheet(
            "QPushButton { background-color: #2f7d5b; color: white; font-weight: bold; "
            "padding: 6px 16px; border-radius: 4px; }"
        )
        self.save_button.clicked.connect(self.save)
        top.addWidget(self.save_button)
        self.cancel_button = QPushButton("Avbryt")
        self.cancel_button.clicked.connect(self._cancel)
        top.addWidget(self.cancel_button)
        layout.addLayout(top)

        splitter = QSplitter()
        self.canvas0 = AnnotationCanvas("cam0")
        self.canvas1 = AnnotationCanvas("cam1")
        splitter.addWidget(self.canvas0)
        splitter.addWidget(self.canvas1)
        splitter.setSizes([640, 640])
        layout.addWidget(splitter, 1)

        self.hint = QLabel(
            "Dra på tom yta för att rita en ny box. Klicka på en box och dra i kanter/hörn "
            "för att ändra storlek. Ctrl+rull zoomar. Del tar bort markerad box."
        )
        self.hint.setStyleSheet("color: #858595;")
        layout.addWidget(self.hint)

        self._populate_classes(class_names)
        self._load_snapshot()

        for canvas in (self.canvas0, self.canvas1):
            canvas.selection_changed.connect(
                lambda box, canvas=canvas: self._on_selection(canvas, box)
            )
            canvas.boxes_changed.connect(self._on_boxes_changed)
        self.class_combo.currentTextChanged.connect(self._on_class_text_changed)
        self.class_combo.activated.connect(lambda _index: self.apply_class())
        if self.class_combo.lineEdit() is not None:
            self.class_combo.lineEdit().returnPressed.connect(self.apply_class)

    def _populate_classes(self, class_names: list[str]) -> None:
        names: list[str] = []
        for name in class_names:
            cleaned = (name or "").strip()
            if cleaned and cleaned not in names:
                names.append(cleaned)
        if not names:
            names = ["object"]
        self._updating_combo = True
        try:
            self.class_combo.clear()
            self.class_combo.addItems(names)
            self.class_combo.setCurrentText(names[0])
        finally:
            self._updating_combo = False
        self.canvas0.set_current_class(names[0])
        self.canvas1.set_current_class(names[0])

    def _load_snapshot(self) -> None:
        for role, canvas in (("cam0", self.canvas0), ("cam1", self.canvas1)):
            frame = self.snapshot.frames.get(role)
            if frame is None:
                continue
            canvas.set_image(frame)
            for detection in self.snapshot.detections.get(role, []):
                annotation = AnnotationBox.from_detection(detection)
                canvas.add_box(annotation)
                self._ensure_class(annotation.class_name)

    def _ensure_class(self, name: str) -> None:
        cleaned = (name or "").strip()
        if not cleaned:
            return
        if self.class_combo.findText(cleaned) < 0:
            self.class_combo.addItem(cleaned)
        self.canvas0.set_current_class(self.class_combo.currentText())
        self.canvas1.set_current_class(self.class_combo.currentText())

    def _on_class_text_changed(self, text: str) -> None:
        if self._updating_combo:
            return
        cleaned = text.strip()
        if cleaned:
            self.canvas0.set_current_class(cleaned)
            self.canvas1.set_current_class(cleaned)
            self._highlight_apply()

    def _highlight_apply(self) -> None:
        self.apply_button.setStyleSheet("font-weight: bold;")

    def _on_selection(self, canvas: AnnotationCanvas, box) -> None:
        self._active_canvas = canvas
        other = self.canvas1 if canvas is self.canvas0 else self.canvas0
        if box is not None:
            other.clear_selection()
            self._updating_combo = True
            try:
                self.class_combo.setCurrentText(box.class_name)
            finally:
                self._updating_combo = False
        self.delete_button.setEnabled(box is not None)

    def _on_boxes_changed(self) -> None:
        self.apply_button.setStyleSheet("")
        self.hint.setText(
            "Dra på tom yta för att rita en ny box. Klicka på en box och dra i kanter/hörn "
            "för att ändra storlek. Ctrl+rull zoomar. Del tar bort markerad box."
        )

    def apply_class(self) -> None:
        class_name = self.class_combo.currentText().strip()
        if not class_name:
            return
        if self.class_combo.findText(class_name) < 0:
            self.class_combo.addItem(class_name)
        self.canvas0.set_current_class(class_name)
        self.canvas1.set_current_class(class_name)
        canvas = self._active_canvas
        box = canvas.selected_box() if canvas is not None else None
        if box is not None:
            box.set_class_name(class_name, class_color(class_name))
        self.apply_button.setStyleSheet("")

    def delete_selected(self) -> None:
        canvas = self._active_canvas
        if canvas is not None:
            canvas.delete_selected()

    def fit_views(self) -> None:
        self.canvas0.fit_to_window()
        self.canvas1.fit_to_window()

    def save(self) -> None:
        annotations = {
            "cam0": self.canvas0.annotations(),
            "cam1": self.canvas1.annotations(),
        }
        if not any(annotations.values()):
            answer = QMessageBox.question(
                self,
                "Inga annoteringar",
                "Inga boxar är ritade. Vill du spara bildparet som negativt exempel?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        try:
            summary = self.dataset_service.add_pair(
                frames=self.snapshot.frames,
                annotations=annotations,
                source={"source": "capture"},
                pair_id=self.snapshot.pair_id,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Kunde inte spara", str(exc))
            return
        self.saved.emit(summary)

    def _cancel(self) -> None:
        self.cancelled.emit()
