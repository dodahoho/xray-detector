import cv2
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from xray_detector.application.dataset_service import DatasetService
from xray_detector.domain.capture import StreamFrame
from xray_detector.domain.detection import Detection

THUMB_HEIGHT = 170
SELECTED_BORDER = "#4da3ff"
SELECTED_BACKGROUND = "#1d3b57"
IDLE_BORDER = "#555"
IDLE_BACKGROUND = "#2b2b2b"


class Thumbnail(QWidget):
    clicked = Signal(object)
    double_clicked = Signal(object)

    def __init__(self, image_id, group_id, pixmap: QPixmap, caption: str, pending: bool = False, parent=None) -> None:
        super().__init__(parent)
        self.image_id = image_id
        self.group_id = group_id
        self.pending = pending
        self.selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 4)
        self.picture = QLabel()
        self.picture.setPixmap(pixmap)
        self.picture.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.caption = QLabel("OSPÅRAD · " + caption if pending else caption)
        if pending:
            self.caption.setStyleSheet("color: #e5a52a; font-weight: bold;")
        self.caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.caption.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.badge = QLabel("MARKERAD")
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge.setStyleSheet(
            f"background: {SELECTED_BORDER}; color: #10202e; font-weight: bold; "
            "border-radius: 3px; padding: 1px 4px;"
        )
        self.badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self.badge)
        layout.addWidget(self.picture)
        layout.addWidget(self.caption)
        self._apply_style()

    def _apply_style(self) -> None:
        border = SELECTED_BORDER if self.selected else IDLE_BORDER
        background = SELECTED_BACKGROUND if self.selected else IDLE_BACKGROUND
        width = 4 if self.selected else 3
        self.setStyleSheet(
            f"Thumbnail {{ background: {background}; border: {width}px solid {border}; "
            "border-radius: 6px; }"
        )
        self.badge.setVisible(self.selected)

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        self._apply_style()

    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self)

    def mouseDoubleClickEvent(self, event) -> None:
        self.double_clicked.emit(self)


class DatasetView(QWidget):
    open_annotation_requested = Signal(object)
    status_changed = Signal(str)

    def __init__(self, dataset: DatasetService, parent=None) -> None:
        super().__init__(parent)
        self.dataset_service = dataset
        self._thumbs: list[Thumbnail] = []
        self._groups: dict[int, list[Thumbnail]] = {}
        self._coco: dict | None = None

        layout = QVBoxLayout(self)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Datasetversion:"))
        self.version_combo = QComboBox()
        self.version_combo.currentIndexChanged.connect(self.refresh)
        bar.addWidget(self.version_combo)
        bar.addStretch(1)
        self.delete_button = QPushButton("Ta bort markerade")
        self.delete_button.clicked.connect(self._on_delete)
        bar.addWidget(self.delete_button)
        layout.addLayout(bar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(4, 4, 4, 4)
        self.content_layout.addStretch(1)
        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll, 1)

        self.refresh_versions()

    def refresh_versions(self) -> None:
        self.version_combo.blockSignals(True)
        self.version_combo.clear()
        for version in self.dataset_service.versions():
            self.version_combo.addItem(f"v{version}", version)
        self.version_combo.blockSignals(False)
        if self.version_combo.count() > 0 and self.version_combo.currentIndex() < 0:
            self.version_combo.setCurrentIndex(self.version_combo.count() - 1)
        self.refresh()

    def refresh(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self._thumbs = []
        self._groups = {}
        self._pending_by_group: dict[str, object] = {}

        self._add_pending_section()
        version_data = self.version_combo.currentData()
        if version_data is None:
            self._coco = None
            if not self._thumbs:
                self.content_layout.addWidget(QLabel("Inga bilder sparade än."))
            self.content_layout.addStretch(1)
            self._update_delete_button()
            return
        version = int(version_data)
        coco = self.dataset_service.load_coco(version)
        self._coco = coco
        annotations_by_image: dict[int, list[dict]] = {}
        for annotation in coco["annotations"]:
            annotations_by_image.setdefault(annotation["image_id"], []).append(annotation)
        category_names = {c["id"]: c["name"] for c in coco["categories"]}

        groups: dict[int, list[dict]] = {}
        for image in coco["images"]:
            key = image.get("group") or image["id"]
            groups.setdefault(key, []).append(image)

        for key in sorted(groups):
            images = sorted(groups[key], key=lambda img: img["id"])
            object_count = sum(len(annotations_by_image.get(img["id"], [])) for img in images)
            header = QLabel(f"Fångst {key} · {len(images)} bilder · {object_count} objekt")
            header.setStyleSheet("font-weight: bold; color: #888;")
            frame = QFrame()
            frame.setFrameShape(QFrame.Shape.Box)
            frame.setStyleSheet("QFrame { border: 1px solid #666; border-radius: 8px; }")
            inner = QVBoxLayout(frame)
            inner.setContentsMargins(8, 8, 8, 8)
            inner.addWidget(header)
            row = QHBoxLayout()
            row.addStretch(1)
            for image in images:
                pixmap = QPixmap(str(self.dataset_service.version_dir(version) / "images" / image["file_name"]))
                pixmap = pixmap.scaledToHeight(THUMB_HEIGHT, Qt.TransformationMode.SmoothTransformation)
                count = len(annotations_by_image.get(image["id"], []))
                classes = sorted(
                    {
                        category_names[ann["category_id"]]
                        for ann in annotations_by_image.get(image["id"], [])
                    }
                )
                caption = "Inga objekt" if not classes else ", ".join(classes) + f" ({count})"
                thumb = Thumbnail(image["id"], key, pixmap, caption)
                thumb.clicked.connect(self._on_thumb_clicked)
                thumb.double_clicked.connect(self._on_thumb_double_clicked)
                row.addWidget(thumb)
                self._thumbs.append(thumb)
                self._groups.setdefault(key, []).append(thumb)
            row.addStretch(1)
            inner.addLayout(row)
            self.content_layout.addWidget(frame)
        self.content_layout.addStretch(1)
        self._update_delete_button()

    def _add_pending_section(self) -> None:
        """Osparade fangster fran pending-kon (krascsakra, TASK-12)."""
        captures = self.dataset_service.pending_captures()
        for capture in captures:
            self._pending_by_group[capture.group_id] = capture
            header = QLabel(f"Osparad fångst {capture.group_id} · {len(capture.frames)} bild(er)")
            header.setStyleSheet("font-weight: bold; color: #e5a52a;")
            frame_box = QFrame()
            frame_box.setFrameShape(QFrame.Shape.Box)
            frame_box.setStyleSheet("QFrame { border: 1px dashed #e5a52a; border-radius: 8px; }")
            inner = QVBoxLayout(frame_box)
            inner.setContentsMargins(8, 8, 8, 8)
            inner.addWidget(header)
            row = QHBoxLayout()
            row.addStretch(1)
            for index, stream_frame in enumerate(capture.frames):
                height, width = stream_frame.frame.shape[:2]
                from PySide6.QtGui import QImage

                rgb = stream_frame.frame[:, :, ::-1].copy()
                image = QImage(rgb.data, width, height, 3 * width, QImage.Format.Format_RGB888).copy()
                pixmap = QPixmap.fromImage(image).scaledToHeight(
                    THUMB_HEIGHT, Qt.TransformationMode.SmoothTransformation
                )
                count = len(stream_frame.detections)
                caption = f"{stream_frame.source_label} · {count} detektion(er)"
                thumb = Thumbnail(capture.group_id, capture.group_id, pixmap, caption, pending=True)
                thumb.clicked.connect(self._on_thumb_clicked)
                thumb.double_clicked.connect(self._on_thumb_double_clicked)
                row.addWidget(thumb)
                self._thumbs.append(thumb)
            row.addStretch(1)
            inner.addLayout(row)
            self.content_layout.addWidget(frame_box)

    def _on_thumb_clicked(self, thumb: Thumbnail) -> None:
        """Markerar hela fångsten - bilderna hanteras alltid som ett par (TASK-25)."""
        selected = not thumb.selected
        for member in self._group_thumbs(thumb):
            member.set_selected(selected)
        self._update_delete_button()

    def _group_thumbs(self, thumb: Thumbnail) -> list[Thumbnail]:
        """Alla bilder som hör till samma fångst som thumb."""
        if thumb.pending:
            return [t for t in self._thumbs if t.pending and t.group_id == thumb.group_id]
        return self._groups.get(thumb.group_id, [thumb])

    def _update_delete_button(self) -> None:
        count = sum(1 for thumb in self._thumbs if thumb.selected)
        self.delete_button.setText(
            f"Ta bort markerade ({count})" if count else "Ta bort markerade"
        )
        self.delete_button.setEnabled(count > 0)

    def _on_thumb_double_clicked(self, thumb: Thumbnail) -> None:
        if thumb.pending:
            capture = self._pending_by_group.get(thumb.group_id)
            if capture is None:
                return
            self.open_annotation_requested.emit(capture)
            return
        group = self._groups.get(thumb.group_id, [thumb])
        frames: list[StreamFrame] = []
        for member in group:
            entry = next(img for img in self._coco["images"] if img["id"] == member.image_id)
            frame = cv2.imread(str(self.dataset_service.version_dir(self._current_version()) / "images" / entry["file_name"]))
            if frame is None:
                continue
            detections = []
            for ann in self._coco["annotations"]:
                if ann["image_id"] != entry["id"]:
                    continue
                x, y, w, h = ann["bbox"]
                class_name = next(
                    c["name"] for c in self._coco["categories"] if c["id"] == ann["category_id"]
                )
                detections.append(
                    Detection(x1=float(x), y1=float(y), x2=float(x + w), y2=float(y + h),
                             class_name=class_name, confidence=1.0)
                )
            frames.append(
                StreamFrame(source_id=f"img{entry['id']}", frame=frame,
                             detections=detections, source_label=entry["file_name"])
            )
        if frames:
            self.open_annotation_requested.emit(frames)

    def _current_version(self) -> int:
        return int(self.version_combo.currentData())

    def _on_delete(self) -> None:
        selected = [thumb for thumb in self._thumbs if thumb.selected]
        pending_ids = list(dict.fromkeys(t.group_id for t in selected if t.pending))
        ids = [t.image_id for t in selected if not t.pending]
        if not ids and not pending_ids:
            self.status_changed.emit("Markera bilder att ta bort först")
            return
        count = len(selected)
        answer = QMessageBox.question(
            self,
            "Ta bort bilder",
            f"Ta bort {count} bild(er) med tillhörande annoteringar? Det går inte att ångra.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        if ids:
            self.dataset_service.delete_images(self._current_version(), ids)
        for group_id in pending_ids:
            self.dataset_service.remove_pending(group_id)
        self.status_changed.emit(f"Tog bort {count} bild(er) från datasetet")
        self.refresh()
