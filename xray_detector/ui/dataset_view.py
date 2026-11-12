from datetime import datetime
from pathlib import Path

import cv2
from PySide6.QtCore import QDate, QPoint, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
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
from xray_detector.ui.colors import class_color
from xray_detector.ui.settings_dialog import (
    SORT_NEWEST,
    DatasetSortSection,
    settings_button,
    sort_order,
)
from xray_detector.ui.shortcuts import mnemonic
from xray_detector.ui.style import button

THUMB_HEIGHT = 170
THUMB_BORDER = 3
SELECTED_BORDER = "#4da3ff"
SELECTED_BACKGROUND = "#1d3b57"
IDLE_BORDER = "#555"
IDLE_BACKGROUND = "#2b2b2b"
UNKNOWN_DATE = "Okänt datum"
ALL_CLASSES = "Alla klasser"
NO_MATCHES = "Inga bilder matchar filtret."
DATE_FORMAT = "yyyy-MM-dd"
HEADER_OBJECT_NAME = "captureHeader"
HEADER_MARGINS = (6, 2, 6, 2)
TIME_BADGE_GAP = 6


class FlowLayout(QLayout):
    """Lägger widgets efter varandra och börjar en ny rad när den är full (TASK-42).

    Qt har inget flödeslayout, så korten skulle annars behöva fasta kolumner.
    Varje widget får sin sizeHint och radbryts mot layoutens bredd, vilket ger
    samma beteende vid alla fönsterbredder.
    """

    def __init__(self, parent=None, spacing: int = 8) -> None:
        super().__init__(parent)
        self._items: list = []
        self._spacing = spacing
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientation:
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._arrange(QRect(0, 0, width, 0), apply=False)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._arrange(rect, apply=True)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        return size + QSize(
            margins.left() + margins.right(), margins.top() + margins.bottom()
        )

    def _arrange(self, rect: QRect, apply: bool) -> int:
        """Placerar korten radvis; returnerar höjden utrymmet behöver."""
        margins = self.contentsMargins()
        area = rect.adjusted(
            margins.left(), margins.top(), -margins.right(), -margins.bottom()
        )
        x = area.x()
        y = area.y()
        line_height = 0
        for item in self._items:
            hint = item.sizeHint()
            next_x = x + hint.width() + self._spacing
            if next_x - self._spacing > area.right() and line_height > 0:
                x = area.x()
                y += line_height + self._spacing
                next_x = x + hint.width() + self._spacing
                line_height = 0
            if apply:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x = next_x
            line_height = max(line_height, hint.height())
        return y + line_height - rect.y() + margins.bottom()


def _ordered_dates(by_date: dict[str, list], newest_first: bool) -> list[str]:
    """Datumen i visningsordning; fångster utan datum hamnar sist (TASK-42)."""
    dates = sorted((date for date in by_date if date), reverse=newest_first)
    if "" in by_date:
        dates.append("")
    return dates


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


def _header_text_style(color: str) -> str:
    """Tidsetiketten: bara färgen, så raden äger ram och bakgrund (TASK-66)."""
    return f"color: {color}; background: transparent; border: none;"


def _header_style(color: str, background: str | None = None) -> str:
    """Rubrikens stil; bara färgerna skiljer så rubriken behåller sin storlek (TASK-63).

    Selektorn pekar på rubrikradens objectName, inte på QFrame: QLabel ärver
    QFrame och skulle annars också få ram och bakgrund.
    """
    fill = f"background: {background}; " if background else ""
    return (
        f"#{HEADER_OBJECT_NAME} {{ font-weight: bold; color: {color}; "
        f"{fill}border-radius: 3px; }}"
    )


def _card_style(color: str, dashed: bool = False) -> str:
    """Kortets ram; samma bredd i alla lägen så kortet inte byter storlek (TASK-63).

    Selektorn pekar på CaptureCard, inte på QFrame: rubrikraden och tidsetiketten
    ärver annars kortets ram, eftersom QLabel ärver QFrame.
    """
    line = "dashed" if dashed else "solid"
    return f"CaptureCard {{ border: 1px {line} {color}; border-radius: 8px; }}"


def _badge(name: str, known_classes: list[str], parent: QWidget) -> QLabel:
    """Klassmärke i rubrikraden, färgat med klassens färg (TASK-66)."""
    color = class_color(name, known_classes)
    text_color = "#111" if color.lightness() > 140 else "#fff"
    badge = QLabel(name, parent)
    badge.setStyleSheet(
        f"QLabel {{ background: {color.name()}; color: {text_color}; "
        "border-radius: 6px; padding: 1px 6px; font-weight: bold; }"
    )
    return badge


def _capture_header(
    text: str,
    color: str,
    parent: QWidget,
    classes: tuple[str, ...] = (),
    known_classes: list[str] | None = None,
) -> tuple[QWidget, QLabel]:
    """Rubrikrad med tid och klassmärken (TASK-66, TASK-68).

    Raden bär färgen och bakgrunden, så markeringen täcker både tiden och
    märkena. Texten är densamma i alla lägen, så märkena hamnar strax efter
    tidsangivelsen och kortet behåller sin storlek när fångsten markeras.
    Märkena får extra luft mot tiden men sitter tätt ihop inbördes.
    """
    row = QFrame(parent)
    row.setObjectName(HEADER_OBJECT_NAME)
    row.setStyleSheet(_header_style(color))
    row.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    row.ensurePolished()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(*HEADER_MARGINS)
    layout.setSpacing(4)
    label = QLabel(text, row)
    label.setStyleSheet(_header_text_style(color))
    layout.addWidget(label)
    if classes:
        layout.addSpacing(TIME_BADGE_GAP)
    for name in classes:
        layout.addWidget(_badge(name, list(known_classes or []), row))
    layout.addStretch(1)
    return row, label


def _thumbnail_pixmap(
    image: QImage,
    annotations: list[dict],
    category_names: dict[int, str],
    known_classes: list[str],
) -> QPixmap:
    """Thumbnail med bildens detektioner inritade (TASK-64).

    Ritas efter nedskalningen, så ramen blir lika tunn på alla bilder. Skalan
    är thumbnailens höjd delad med originalbildens, vilket gäller båda axlarna
    eftersom scaledToHeight behåller bildförhållandet.
    """
    pixmap = QPixmap.fromImage(image).scaledToHeight(
        THUMB_HEIGHT, Qt.TransformationMode.SmoothTransformation
    )
    if not annotations or image.height() == 0:
        return pixmap
    scale = pixmap.height() / image.height()
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen()
    pen.setWidth(2)
    for annotation in annotations:
        x, y, width, height = annotation["bbox"]
        pen.setColor(class_color(category_names[annotation["category_id"]], known_classes))
        painter.setPen(pen)
        painter.drawRect(QRectF(x * scale, y * scale, width * scale, height * scale))
    painter.end()
    return pixmap


class CaptureCard(QFrame):
    """Kort för en fångst; hela ytan markerar fångsten (TASK-65).

    Thumbnails hanterar sina egna klick, så ett klick på en bild växlar en gång.
    Klick på rubrik, klassmärken och kortets marginal når hit i stället.
    """

    clicked = Signal(object)

    def __init__(self, group_id, parent=None) -> None:
        super().__init__(parent)
        self.group_id = group_id
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self)


class Thumbnail(QWidget):
    clicked = Signal(object)
    double_clicked = Signal(object)

    def __init__(
        self,
        image_id,
        group_id,
        pixmap: QPixmap,
        pending: bool = False,
        tooltip: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.image_id = image_id
        self.group_id = group_id
        self.pending = pending
        self.selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if tooltip:
            self.setToolTip(tooltip)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        self.picture = QLabel()
        self.picture.setPixmap(pixmap)
        self.picture.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self.picture)
        self._apply_style()

    def _apply_style(self) -> None:
        """Bara färgen växlar; samma rambredd håller bildens storlek fast (TASK-63)."""
        border = SELECTED_BORDER if self.selected else IDLE_BORDER
        background = SELECTED_BACKGROUND if self.selected else IDLE_BACKGROUND
        self.setStyleSheet(
            f"Thumbnail {{ background: {background}; border: {THUMB_BORDER}px solid {border}; "
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
        self._section_headings: dict[str, QLabel] = {}
        self._section_cards: dict[str, QWidget] = {}
        self._coco: dict | None = None
        self._pending_by_group: dict[str, object] = {}
        self._refresh_task: BackgroundTask | None = None
        self._refresh_pending = False
        self._export_task: BackgroundTask | None = None
        self._export_label = ""
        self._data: dict | None = None
        self._date_bounds_ready = False

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

        filters = QHBoxLayout()
        filters.addWidget(QLabel("Klass:"))
        self.class_combo = QComboBox()
        self.class_combo.addItem(ALL_CLASSES, None)
        self.class_combo.currentIndexChanged.connect(self._on_filter_changed)
        filters.addWidget(self.class_combo)
        filters.addSpacing(12)
        self.date_filter = QCheckBox("Datumintervall")
        self.date_filter.toggled.connect(self._on_date_filter_toggled)
        filters.addWidget(self.date_filter)
        self.date_from = QDateEdit()
        self.date_to = QDateEdit()
        for widget in (self.date_from, self.date_to):
            widget.setCalendarPopup(True)
            widget.setDisplayFormat(DATE_FORMAT)
            widget.setEnabled(False)
            widget.dateChanged.connect(self._on_filter_changed)
            filters.addWidget(widget)
            if widget is self.date_from:
                filters.addWidget(QLabel("till"))
        filters.addStretch(1)
        layout.addLayout(filters)

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
        self._data = data
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self._thumbs = []
        self._groups = {}
        self._group_headers = {}
        self._section_headings = {}
        self._section_cards = {}
        self._pending_by_group = {}

        newest_first = sort_order(self.settings) == SORT_NEWEST
        coco = data["coco"]
        self._coco = coco
        known_classes = [c["name"] for c in coco["categories"]]
        annotations_by_image: dict[int, list[dict]] = {}
        for annotation in coco["annotations"]:
            annotations_by_image.setdefault(annotation["image_id"], []).append(annotation)
        category_names = {c["id"]: c["name"] for c in coco["categories"]}

        groups: dict[int, list[dict]] = {}
        for image in coco["images"]:
            key = image.get("group") or image["id"]
            groups.setdefault(key, []).append(image)

        by_date: dict[str, list] = {}
        for key in sorted(groups, reverse=newest_first):
            images = sorted(groups[key], key=lambda img: img["id"])
            stamp = _format_timestamp(images[0].get("captured")) or _mtime_timestamp(
                self.dataset_service.images_dir / images[0]["file_name"]
            )
            by_date.setdefault(stamp[:10], []).append((key, images, stamp))

        self._sync_filters(
            self._filter_classes(coco, data["pending"]),
            self._capture_days(data, by_date),
        )
        self._add_pending_section(data["pending"], newest_first, known_classes)
        if not coco["images"]:
            if not self._thumbs:
                self.content_layout.addWidget(QLabel("Inga bilder sparade än."))
            self.content_layout.addStretch(1)
            self._update_delete_button()
            return

        selected_class = self.class_combo.currentData()
        date_range = self._selected_date_range()
        visible: dict[str, list] = {}
        for date in _ordered_dates(by_date, newest_first):
            for key, images, stamp in by_date[date]:
                classes = {
                    category_names[ann["category_id"]]
                    for image in images
                    for ann in annotations_by_image.get(image["id"], [])
                }
                if self._matches(classes, stamp, selected_class, date_range):
                    visible.setdefault(date, []).append((key, images, stamp))

        for date, entries in visible.items():
            cards = self._add_section(date or UNKNOWN_DATE)
            for key, images, stamp in entries:
                self._add_capture_card(
                    cards,
                    key,
                    images,
                    stamp,
                    annotations_by_image,
                    category_names,
                    known_classes,
                    data["images"],
                )
        if not self._thumbs:
            self.content_layout.addWidget(QLabel(NO_MATCHES))
        self.content_layout.addStretch(1)
        self._update_delete_button()

    def _capture_days(self, data: dict, by_date: dict[str, list]) -> list[str]:
        """Alla datum som finns i listan, för datumfiltrets gränser (TASK-67)."""
        days = [date for date in by_date if date]
        for capture in data["pending"]:
            stamp = _format_timestamp(capture.saved_at) or _mtime_timestamp(
                capture.directory
            )
            if stamp:
                days.append(stamp[:10])
        return days

    def _filter_classes(self, coco: dict, pending) -> list[str]:
        """Klasserna som går att filtrera på: datasetets och de osparades (TASK-67)."""
        names = [category["name"] for category in coco["categories"]]
        detected = {
            detection.class_name
            for capture in pending
            for stream_frame in capture.frames
            for detection in stream_frame.detections
        }
        return names + sorted(detected - set(names))

    def _sync_filters(self, class_names: list[str], days: list[str]) -> None:
        """Fyller klasslistan och datumgränserna från datasetet (TASK-67).

        Användarens val behålls: klassvalet matchas på namn och datumgränserna
        sätts bara första gången det finns datum att sätta dem från.
        """
        current = self.class_combo.currentData()
        self.class_combo.blockSignals(True)
        self.class_combo.clear()
        self.class_combo.addItem(ALL_CLASSES, None)
        for name in class_names:
            self.class_combo.addItem(name, name)
        self.class_combo.setCurrentIndex(max(self.class_combo.findData(current), 0))
        self.class_combo.blockSignals(False)
        if self._date_bounds_ready or not days:
            return
        for widget, value in ((self.date_from, min(days)), (self.date_to, max(days))):
            widget.blockSignals(True)
            widget.setDate(QDate.fromString(value, DATE_FORMAT))
            widget.blockSignals(False)
        self._date_bounds_ready = True

    def _selected_date_range(self) -> tuple[str, str] | None:
        """Valt datumintervall som ISO-datum, eller None när filtret är av."""
        if not self.date_filter.isChecked():
            return None
        return (
            self.date_from.date().toString(DATE_FORMAT),
            self.date_to.date().toString(DATE_FORMAT),
        )

    def _matches(
        self,
        classes: set[str],
        stamp: str,
        selected_class: str | None,
        date_range: tuple[str, str] | None,
    ) -> bool:
        """Om en fångst passerar klass- och datumfiltret (TASK-67)."""
        if selected_class is not None and selected_class not in classes:
            return False
        if date_range is not None:
            day = stamp[:10]
            if not day or not date_range[0] <= day <= date_range[1]:
                return False
        return True

    def _on_filter_changed(self, *_args) -> None:
        """Bygger om listan med de nya filtren; datan läses inte om (TASK-67)."""
        if self._data is not None:
            self._build(self._data)

    def _on_date_filter_toggled(self, checked: bool) -> None:
        """Slår på eller av datumintervallet och bygger om listan (TASK-67)."""
        self.date_from.setEnabled(checked)
        self.date_to.setEnabled(checked)
        self._on_filter_changed()

    def _add_section(self, title: str, *, pending: bool = False) -> FlowLayout:
        """Sektion med rubrik och en rad kort som radbryts (TASK-42)."""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        heading = QLabel(title)
        color = "#e5a52a" if pending else "#aaa"
        heading.setStyleSheet(
            f"font-weight: bold; color: {color}; "
            "border-bottom: 1px solid #444; padding-bottom: 2px;"
        )
        layout.addWidget(heading)
        cards = QWidget()
        flow = FlowLayout(cards, spacing=8)
        layout.addWidget(cards)
        self.content_layout.addWidget(section)
        self._section_headings[title] = heading
        self._section_cards[title] = cards
        return flow

    def _add_capture_card(
        self,
        cards: FlowLayout,
        key,
        images: list[dict],
        stamp: str,
        annotations_by_image: dict[int, list[dict]],
        category_names: dict[int, str],
        known_classes: list[str],
        decoded: dict,
    ) -> None:
        """Ett kort per fångst: tid, klassmärken och bildparet (TASK-42, TASK-66)."""
        classes = tuple(
            sorted(
                {
                    category_names[ann["category_id"]]
                    for img in images
                    for ann in annotations_by_image.get(img["id"], [])
                }
            )
        )
        time_label = stamp[11:] if stamp else f"Fångst {key}"
        card = CaptureCard(key)
        card.setFrameShape(QFrame.Shape.Box)
        card.setStyleSheet(_card_style("#666"))
        card.clicked.connect(self._on_card_clicked)
        header, header_label = _capture_header(
            time_label, "#888", card, classes, known_classes
        )
        self._group_headers[key] = (header_label, card)
        inner = QVBoxLayout(card)
        inner.setContentsMargins(8, 8, 8, 8)
        inner.setSpacing(4)
        inner.addWidget(header)
        row = QHBoxLayout()
        row.setSpacing(4)
        for image in images:
            annotations = annotations_by_image.get(image["id"], [])
            pixmap = _thumbnail_pixmap(
                decoded[image["id"]], annotations, category_names, known_classes
            )
            thumb = Thumbnail(image["id"], key, pixmap)
            thumb.clicked.connect(self._on_thumb_clicked)
            thumb.double_clicked.connect(self._on_thumb_double_clicked)
            row.addWidget(thumb)
            self._thumbs.append(thumb)
            self._groups.setdefault(key, []).append(thumb)
        inner.addLayout(row)
        cards.addWidget(card)

    def _add_pending_section(
        self, captures, newest_first: bool = True, known_classes: list[str] | None = None
    ) -> None:
        """Osparade fångster i en egen sektion överst (TASK-12, TASK-42)."""
        if not captures:
            return
        selected_class = self.class_combo.currentData()
        date_range = self._selected_date_range()
        visible = []
        for capture in captures:
            stamp = _format_timestamp(capture.saved_at) or _mtime_timestamp(
                capture.directory
            )
            classes = {
                detection.class_name
                for stream_frame in capture.frames
                for detection in stream_frame.detections
            }
            if self._matches(classes, stamp, selected_class, date_range):
                visible.append((capture, stamp))
        if not visible:
            return
        if not newest_first:
            visible.reverse()
        cards = self._add_section("Osparade fångster", pending=True)
        for capture, stamp in visible:
            self._pending_by_group[capture.group_id] = capture
            title = f"Osparad · {stamp}" if stamp else f"Osparad fångst {capture.group_id}"
            classes = tuple(
                sorted(
                    {
                        detection.class_name
                        for stream_frame in capture.frames
                        for detection in stream_frame.detections
                    }
                )
            )
            card = CaptureCard(capture.group_id)
            card.setFrameShape(QFrame.Shape.Box)
            card.setStyleSheet(_card_style("#e5a52a", dashed=True))
            card.clicked.connect(self._on_card_clicked)
            header, header_label = _capture_header(
                title, "#e5a52a", card, classes, known_classes
            )
            self._group_headers[capture.group_id] = (header_label, card)
            inner = QVBoxLayout(card)
            inner.setContentsMargins(8, 8, 8, 8)
            inner.setSpacing(4)
            inner.addWidget(header)
            row = QHBoxLayout()
            row.setSpacing(4)
            for stream_frame in capture.frames:
                height, width = stream_frame.frame.shape[:2]
                rgb = stream_frame.frame[:, :, ::-1].copy()
                image = QImage(rgb.data, width, height, 3 * width, QImage.Format.Format_RGB888).copy()
                pixmap = QPixmap.fromImage(image).scaledToHeight(
                    THUMB_HEIGHT, Qt.TransformationMode.SmoothTransformation
                )
                count = len(stream_frame.detections)
                thumb = Thumbnail(
                    capture.group_id,
                    capture.group_id,
                    pixmap,
                    pending=True,
                    tooltip=f"{stream_frame.source_label} · {count} detektion(er)",
                )
                thumb.clicked.connect(self._on_thumb_clicked)
                thumb.double_clicked.connect(self._on_thumb_double_clicked)
                row.addWidget(thumb)
                self._thumbs.append(thumb)
            inner.addLayout(row)
            cards.addWidget(card)

    def _on_thumb_clicked(self, thumb: Thumbnail) -> None:
        """Markerar hela fångsten - bilderna hanteras alltid som ett par (TASK-25)."""
        self._toggle_group(thumb.group_id)

    def _on_card_clicked(self, card: CaptureCard) -> None:
        """Samma växling när klicket hamnar utanför bilderna (TASK-65)."""
        self._toggle_group(card.group_id)

    def _toggle_group(self, group_id) -> None:
        """Växlar markeringen för fångstens alla bilder."""
        selected = not any(thumb.selected for thumb in self._thumbs_for_group(group_id))
        for member in self._thumbs_for_group(group_id):
            member.set_selected(selected)
        self._update_group_header(group_id)
        self._update_delete_button()

    def _thumbs_for_group(self, group_id) -> list[Thumbnail]:
        """Alla bilder som hör till samma fångst."""
        return [thumb for thumb in self._thumbs if thumb.group_id == group_id]

    def _update_group_header(self, group_id) -> None:
        """Färgar fångstens rubrikrad efter markeringen (TASK-29, TASK-68).

        Bara färgerna växlar; texten står still och ramens bredd är fast, så
        kortet behåller sin storlek och vyn inte hoppar (TASK-63).
        """
        entry = self._group_headers.get(group_id)
        if entry is None:
            return
        header, frame = entry
        row = header.parentWidget()
        members = self._thumbs_for_group(group_id)
        selected = any(thumb.selected for thumb in members)
        pending = any(thumb.pending for thumb in members)
        if selected:
            row.setStyleSheet(_header_style("#10202e", SELECTED_BORDER))
            header.setStyleSheet(_header_text_style("#10202e"))
            frame.setStyleSheet(_card_style(SELECTED_BORDER))
        elif pending:
            row.setStyleSheet(_header_style("#e5a52a"))
            header.setStyleSheet(_header_text_style("#e5a52a"))
            frame.setStyleSheet(_card_style("#e5a52a", dashed=True))
        else:
            row.setStyleSheet(_header_style("#888"))
            header.setStyleSheet(_header_text_style("#888"))
            frame.setStyleSheet(_card_style("#666"))

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
