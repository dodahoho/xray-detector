"""AnnotationView – vy med två frysta bilder, klasspanel och spara/avbryt.

Flöde:
1. Får två frames + (valfria) befintliga detektioner från detektionsläget.
2. Användaren ritar/redigerar rektanglar och väljer klasser.
3. Spara → skickar frames + annotations till DatasetManager → signal saved.
"""
from __future__ import annotations

import numpy as np
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from xray_detector.annotation.annotation_canvas import AnnotationCanvas, RectItem
from xray_detector.detection.model_registry import Detection


class AnnotationView(QWidget):
    """Annoteringsläget."""

    saved = Signal()          # sparat, återgå till detektionsläge
    cancelled = Signal()      # avbrutet

    def __init__(self, classes: list[str], parent=None):
        super().__init__(parent)
        self.classes = list(classes)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        # Övre rad: två canvases
        canvases = QHBoxLayout()
        self.canvas_left = AnnotationCanvas()
        self.canvas_right = AnnotationCanvas()
        self.canvas_left.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas_right.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        canvases.addWidget(self.canvas_left)
        canvases.addWidget(self.canvas_right)
        root.addLayout(canvases, stretch=1)

        # Klasspanel
        class_row = QHBoxLayout()
        class_row.addWidget(QLabel("Klass:"))
        self.class_combo = QComboBox()
        self.class_combo.addItems(self.classes)
        self.class_combo.setMinimumWidth(180)
        class_row.addWidget(self.class_combo)

        self.new_class_edit = QLineEdit()
        self.new_class_edit.setPlaceholderText("Ny klass (skriv + Enter)")
        self.new_class_edit.setFixedWidth(200)
        self.new_class_edit.returnPressed.connect(self._add_new_class)
        class_row.addWidget(self.new_class_edit)
        class_row.addStretch(1)
        root.addLayout(class_row)

        # Knappar
        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Spara i dataset")
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self._save)
        self.cancel_btn = QPushButton("Avbryt")
        self.cancel_btn.clicked.connect(self.cancelled.emit)
        btn_row.addStretch(1)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.save_btn)
        root.addLayout(btn_row)

        # Koppla klassval → canvas
        self.class_combo.currentTextChanged.connect(self._on_class_changed)
        self.canvas_left.selection_changed.connect(self._on_selection_left)
        self.canvas_right.selection_changed.connect(self._on_selection_right)

    # ---- Datainmatning ----
    def set_images(
        self,
        left: np.ndarray | None,
        right: np.ndarray | None,
        left_dets: list[Detection] | None = None,
        right_dets: list[Detection] | None = None,
    ) -> None:
        """Sätt frysta bilder och förinrita befintliga detektioner.

        En sida får vara ``None`` när motsvarande videokälla saknas; vyn visar
        då "Ingen videokälla" och inga rektanglar kan ritas där.
        """
        self.canvas_left.set_image(left)
        self.canvas_right.set_image(right)
        if left is not None:
            for d in (left_dets or []):
                self.canvas_left.add_rect(d.x1, d.y1, d.x2 - d.x1, d.y2 - d.y1, d.class_name)
        if right is not None:
            for d in (right_dets or []):
                self.canvas_right.add_rect(d.x1, d.y1, d.x2 - d.x1, d.y2 - d.y1, d.class_name)

    # ---- Klasshantering ----
    def _add_new_class(self) -> None:
        name = self.new_class_edit.text().strip()
        if name and name not in self.classes:
            self.classes.append(name)
            self.class_combo.addItem(name)
            self.new_class_edit.clear()
            self.class_combo.setCurrentText(name)

    def _on_class_changed(self, name: str) -> None:
        """När klass väljs: säll default för nya rektanglar + uppdatera vald rektangel."""
        self.canvas_left.default_class = name
        self.canvas_right.default_class = name
        # Om en rektangel är vald, ändra dess klass
        for canvas in (self.canvas_left, self.canvas_right):
            r = canvas.selected_rect()
            if r is not None:
                canvas.set_rect_class(r, name)

    def _on_selection_left(self, rect: RectItem | None) -> None:
        if rect is not None:
            self.class_combo.blockSignals(True)
            self.class_combo.setCurrentText(rect.class_name)
            self.class_combo.blockSignals(False)

    def _on_selection_right(self, rect: RectItem | None) -> None:
        if rect is not None:
            self.class_combo.blockSignals(True)
            self.class_combo.setCurrentText(rect.class_name)
            self.class_combo.blockSignals(False)

    # ---- Spara ----
    def _collect(self, canvas: AnnotationCanvas) -> list[dict]:
        """Samla rektanglar från en canvas som list av dict."""
        out = []
        for r in canvas.rects():
            rect = r.rect()
            out.append({
                "class_name": r.class_name or "okänd",
                "x": rect.left(),
                "y": rect.top(),
                "w": rect.width(),
                "h": rect.height(),
            })
        return out

    def _save(self) -> None:
        # Data exponeras via egenskaper som appen läser
        self._left_annotations = self._collect(self.canvas_left)
        self._right_annotations = self._collect(self.canvas_right)
        self.saved.emit()

    # ---- Accessors för appen ----
    @property
    def left_image(self) -> np.ndarray | None:
        return self.canvas_left.image

    @property
    def right_image(self) -> np.ndarray | None:
        return self.canvas_right.image

    @property
    def left_annotations(self) -> list[dict]:
        return getattr(self, "_left_annotations", [])

    @property
    def right_annotations(self) -> list[dict]:
        return getattr(self, "_right_annotations", [])
