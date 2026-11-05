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

from xray_detector.capture.camera_service import StreamFrame
from xray_detector.dataset.store import DatasetStore
from xray_detector.detection.base import Detection

THUMB_HEIGHT = 170
SELECTED_BORDER = "#2a82da"


class Thumbnail(QWidget):
    clicked = Signal(object)
    double_clicked = Signal(object)

    def __init__(self, image_id: int, group_id: int, pixmap: QPixmap, caption: str, parent=None) -> None:
        super().__init__(parent)
        self.image_id = image_id
        self.group_id = group_id
        self.selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 4)
        self.picture = QLabel()
        self.picture.setPixmap(pixmap)
        self.picture.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.caption = QLabel(caption)
        self.caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.caption.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self.picture)
        layout.addWidget(self.caption)
        self._apply_style()

    def _apply_style(self) -> None:
        border = SELECTED_BORDER if self.selected else "#555"
        self.setStyleSheet(
            f"Thumbnail {{ background: #2b2b2b; border: 3px solid {border}; border-radius: 6px; }}"
        )

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

    def __init__(self, store: DatasetStore, parent=None) -> None:
        super().__init__(parent)
        self.store = store
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
        for version in self.store.versions():
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

        version_data = self.version_combo.currentData()
        if version_data is None:
            self._coco = None
            self.content_layout.addWidget(QLabel("Inga bilder sparade än."))
            self.content_layout.addStretch(1)
            return
        version = int(version_data)
        coco = self.store.load_coco(version)
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
                pixmap = QPixmap(str(self.store.version_dir(version) / "images" / image["file_name"]))
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

    def _selected_ids(self) -> list[int]:
        return [thumb.image_id for thumb in self._thumbs if thumb.selected]

    def _on_thumb_clicked(self, thumb: Thumbnail) -> None:
        thumb.set_selected(not thumb.selected)

    def _on_thumb_double_clicked(self, thumb: Thumbnail) -> None:
        group = self._groups.get(thumb.group_id, [thumb])
        frames: list[StreamFrame] = []
        for member in group:
            entry = next(img for img in self._coco["images"] if img["id"] == member.image_id)
            frame = cv2.imread(str(self.store.version_dir(self._current_version()) / "images" / entry["file_name"]))
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
        ids = self._selected_ids()
        if not ids:
            self.status_changed.emit("Markera bilder att ta bort först")
            return
        answer = QMessageBox.question(
            self,
            "Ta bort bilder",
            f"Ta bort {len(ids)} bild(er) med tillhörande annoteringar? Det går inte att ångra.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.store.delete_images(self._current_version(), ids)
        self.status_changed.emit(f"Tog bort {len(ids)} bild(er) från datasetet")
        self.refresh()
