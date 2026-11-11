from datetime import datetime
from pathlib import Path

import cv2
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from xray_detector.application.background_task import BackgroundTask
from xray_detector.application.dataset_service import DatasetService
from xray_detector.domain.capture import StreamFrame
from xray_detector.domain.config import AppConfig
from xray_detector.domain.detection import Detection
from xray_detector.ui.busy_indicator import BusyIndicator
from xray_detector.ui.settings_dialog import (
    SORT_NEWEST,
    DatasetSortSection,
    settings_button,
    sort_order,
)
from xray_detector.ui.shortcuts import mnemonic
from xray_detector.ui.style import button

THUMB_HEIGHT = 170
SELECTED_BORDER = "#4da3ff"
SELECTED_BACKGROUND = "#1d3b57"
IDLE_BORDER = "#555"
IDLE_BACKGROUND = "#2b2b2b"


def _format_timestamp(value: str | None) -> str:
    """ISO-tid till lokal 'YYYY-MM-DD HH:MM:SS'; tom sträng om den saknas."""
    if not value:
        return ""
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return ""
    if moment.tzinfo is not None:
        moment = moment.astimezone()
    return moment.strftime("%Y-%m-%d %H:%M:%S")


def _mtime_timestamp(path: Path) -> str:
    """Fallback för äldre dataset: bildfilens egen tidsstämpel."""
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    except OSError:
        return ""


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

    def __init__(self, config: AppConfig, dataset: DatasetService, settings, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.dataset_service = dataset
        self.settings = settings
        self._thumbs: list[Thumbnail] = []
        self._groups: dict[int, list[Thumbnail]] = {}
        self._group_headers: dict = {}
        self._coco: dict | None = None
        self._pending_by_group: dict[str, object] = {}
        self._refresh_task: BackgroundTask | None = None
        self._refresh_pending = False
        self._export_task: BackgroundTask | None = None
        self._export_label = ""

        layout = QVBoxLayout(self)
        bar = QHBoxLayout()
        bar.addStretch(1)
        self.export_coco_button = button(mnemonic("Exportera COCO", "E"))
        self.export_coco_button.clicked.connect(self._on_export_coco)
        bar.addWidget(self.export_coco_button)
        self.export_yolo_button = button(mnemonic("Exportera YOLO", "Y"))
        self.export_yolo_button.clicked.connect(self._on_export_yolo)
        bar.addWidget(self.export_yolo_button)
        self.delete_button = button(mnemonic("Ta bort markerade", "B"))
        self.delete_button.clicked.connect(self._on_delete)
        bar.addWidget(self.delete_button)
        self.settings_button = settings_button(
            self, "Inställningar – Dataset", self._settings_sections
        )
        bar.addWidget(self.settings_button)
        layout.addLayout(bar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(4, 4, 4, 4)
        self.content_layout.addStretch(1)
        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll, 1)

        self.busy = BusyIndicator(self)
        self.refresh()

    def _settings_sections(self) -> list:
        """Vyns egna inställningar; en ny sortering bygger om listan (TASK-56)."""
        section = DatasetSortSection(self.settings)
        section.order_changed.connect(self.refresh)
        return [section]

    def refresh(self) -> None:
        """Bygger om bildlistan; bilderna dekodas i en arbetstråd (TASK-40)."""
        if self._refresh_task is not None:
            # en omladdning pågår: kör en ny när den är klar så sista läget vinner
            self._refresh_pending = True
            return
        if not self.busy.is_busy():
            # en pågående export äger indikatorn och sin egen text
            self.busy.start("Bygger bildlistan...")
        task = BackgroundTask(self._load)
        task.succeeded.connect(self._build)
        task.failed.connect(self._on_load_failed)
        task.finished.connect(self._on_refresh_finished)
        self._refresh_task = task
        task.start()

    def _load(self) -> dict:
        """Läser datasetet och dekoder bilderna utan att röra widgets (TASK-40).

        Bildavkodningen är den dyra delen: mätt 826 av 870 ms för 200 bilder.
        QImage får skapas utanför GUI-tråden, QPixmap får det inte.
        """
        pending = self.dataset_service.pending_captures()
        coco = self.dataset_service.load_coco()
        images_dir = self.dataset_service.images_dir
        decoded = {
            image["id"]: QImage(str(images_dir / image["file_name"]))
            for image in coco["images"]
        }
        return {"coco": coco, "images": decoded, "pending": pending}

    def _on_load_failed(self, message: str) -> None:
        self.status_changed.emit(f"Kunde inte läsa datasetet: {message}")

    def _on_refresh_finished(self) -> None:
        self._refresh_task = None
        self._update_busy()
        if self._refresh_pending:
            self._refresh_pending = False
            self.refresh()

    def _update_busy(self) -> None:
        """Stänger indikatorn först när varken omladdning eller export pågår."""
        if self._refresh_task is None and self._export_task is None:
            self.busy.stop()

    def wait_for_refresh(self, timeout_ms: int = 10000) -> None:
        """Väntar in en pågående omladdning (tester och stängning)."""
        while self._refresh_task is not None:
            if not self._refresh_task.wait(timeout_ms):
                return

    def _on_export_coco(self) -> None:
        self._start_export("COCO", self.dataset_service.export_coco)

    def _on_export_yolo(self) -> None:
        self._start_export("YOLO", self.dataset_service.export_yolo)

    def _start_export(self, label: str, export) -> None:
        """Exporterar i en arbetstråd medan indikatorn visas (TASK-40)."""
        if self._export_task is not None:
            return
        self._export_label = label
        self.busy.start(f"Exporterar {label}...")
        self._set_export_enabled(False)
        task = BackgroundTask(lambda: export(self.config.export_dir))
        task.succeeded.connect(self._on_export_done)
        task.failed.connect(self._on_export_failed)
        task.finished.connect(self._on_export_finished)
        self._export_task = task
        task.start()

    def _set_export_enabled(self, enabled: bool) -> None:
        self.export_coco_button.setEnabled(enabled)
        self.export_yolo_button.setEnabled(enabled)

    def _on_export_done(self, out) -> None:
        self.status_changed.emit(f"Exporterade {self._export_label} till {out}")

    def _on_export_failed(self, message: str) -> None:
        self.status_changed.emit(f"Export av {self._export_label} misslyckades: {message}")

    def _on_export_finished(self) -> None:
        self._export_task = None
        self._update_busy()
        self._set_export_enabled(True)

    def wait_for_export(self, timeout_ms: int = 10000) -> None:
        """Väntar in en pågående export (tester och stängning)."""
        if self._export_task is not None:
            self._export_task.wait(timeout_ms)

    def _build(self, data: dict) -> None:
        """Ritar listan i GUI-tråden från det arbetstråden läste (TASK-40)."""
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self._thumbs = []
        self._groups = {}
        self._group_headers = {}
        self._pending_by_group = {}

        newest_first = sort_order(self.settings) == SORT_NEWEST
        self._add_pending_section(data["pending"], newest_first)
        coco = data["coco"]
        self._coco = coco
        if not coco["images"]:
            if not self._thumbs:
                self.content_layout.addWidget(QLabel("Inga bilder sparade än."))
            self.content_layout.addStretch(1)
            self._update_delete_button()
            return
        annotations_by_image: dict[int, list[dict]] = {}
        for annotation in coco["annotations"]:
            annotations_by_image.setdefault(annotation["image_id"], []).append(annotation)
        category_names = {c["id"]: c["name"] for c in coco["categories"]}

        groups: dict[int, list[dict]] = {}
        for image in coco["images"]:
            key = image.get("group") or image["id"]
            groups.setdefault(key, []).append(image)

        for key in sorted(groups, reverse=newest_first):
            images = sorted(groups[key], key=lambda img: img["id"])
            object_count = sum(len(annotations_by_image.get(img["id"], [])) for img in images)
            stamp = _format_timestamp(images[0].get("captured")) or _mtime_timestamp(
                self.dataset_service.images_dir / images[0]["file_name"]
            )
            title = stamp or f"Fångst {key}"
            header = QLabel(f"{title} · {len(images)} bilder · {object_count} objekt")
            header.setStyleSheet("font-weight: bold; color: #888;")
            frame = QFrame()
            frame.setFrameShape(QFrame.Shape.Box)
            frame.setStyleSheet("QFrame { border: 1px solid #666; border-radius: 8px; }")
            self._group_headers[key] = (header, frame, header.text())
            inner = QVBoxLayout(frame)
            inner.setContentsMargins(8, 8, 8, 8)
            inner.addWidget(header)
            row = QHBoxLayout()
            row.addStretch(1)
            for image in images:
                pixmap = QPixmap.fromImage(data["images"][image["id"]])
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

    def _add_pending_section(self, captures, newest_first: bool = True) -> None:
        """Osparade fangster fran pending-kon (krascsakra, TASK-12)."""
        ordered = captures if newest_first else reversed(captures)
        for capture in ordered:
            self._pending_by_group[capture.group_id] = capture
            stamp = _format_timestamp(capture.saved_at) or _mtime_timestamp(capture.directory)
            title = f"Osparad · {stamp}" if stamp else f"Osparad fångst {capture.group_id}"
            header = QLabel(f"{title} · {len(capture.frames)} bild(er)")
            header.setStyleSheet("font-weight: bold; color: #e5a52a;")
            frame_box = QFrame()
            frame_box.setFrameShape(QFrame.Shape.Box)
            frame_box.setStyleSheet("QFrame { border: 1px dashed #e5a52a; border-radius: 8px; }")
            self._group_headers[capture.group_id] = (header, frame_box, header.text())
            inner = QVBoxLayout(frame_box)
            inner.setContentsMargins(8, 8, 8, 8)
            inner.addWidget(header)
            row = QHBoxLayout()
            row.addStretch(1)
            for index, stream_frame in enumerate(capture.frames):
                height, width = stream_frame.frame.shape[:2]
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
        for member in self._thumbs_for_group(thumb.group_id):
            member.set_selected(selected)
        self._update_group_header(thumb.group_id)
        self._update_delete_button()

    def _thumbs_for_group(self, group_id) -> list[Thumbnail]:
        """Alla bilder som hör till samma fångst."""
        return [thumb for thumb in self._thumbs if thumb.group_id == group_id]

    def _update_group_header(self, group_id) -> None:
        """Fyller fångstens rubrikrad och avslutar den med 'Markerad' (TASK-29)."""
        entry = self._group_headers.get(group_id)
        if entry is None:
            return
        header, frame, base_text = entry
        members = self._thumbs_for_group(group_id)
        selected = any(thumb.selected for thumb in members)
        pending = any(thumb.pending for thumb in members)
        header.setText(f"{base_text} · Markerad" if selected else base_text)
        if selected:
            header.setStyleSheet(
                f"font-weight: bold; color: #10202e; background: {SELECTED_BORDER}; "
                "border-radius: 3px; padding: 2px 6px;"
            )
            frame.setStyleSheet(
                f"QFrame {{ border: 2px solid {SELECTED_BORDER}; border-radius: 8px; }}"
            )
        elif pending:
            header.setStyleSheet("font-weight: bold; color: #e5a52a;")
            frame.setStyleSheet("QFrame { border: 1px dashed #e5a52a; border-radius: 8px; }")
        else:
            header.setStyleSheet("font-weight: bold; color: #888;")
            frame.setStyleSheet("QFrame { border: 1px solid #666; border-radius: 8px; }")

    def _update_delete_button(self) -> None:
        count = sum(1 for thumb in self._thumbs if thumb.selected)
        label = f"Ta bort markerade ({count})" if count else "Ta bort markerade"
        self.delete_button.setText(mnemonic(label, "B"))
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
            frame = cv2.imread(str(self.dataset_service.images_dir / entry["file_name"]))
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
            self.dataset_service.delete_images(ids)
        for group_id in pending_ids:
            self.dataset_service.remove_pending(group_id)
        self.status_changed.emit(f"Tog bort {count} bild(er) från datasetet")
        self.refresh()
