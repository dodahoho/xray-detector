from datetime import datetime
from pathlib import Path

import cv2
from PySide6.QtCore import QDate, QRectF, Qt, Signal
from PySide6.QtGui import QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from xray_detector.application.background_task import BackgroundTask
from xray_detector.domain.capture import StreamFrame
from xray_detector.domain.config import AppConfig
from xray_detector.domain.dataset import capture_group, describe
from xray_detector.domain.detection import Detection
from xray_detector.infrastructure.dataset_store.export import export_coco, export_yolo
from xray_detector.infrastructure.dataset_store.pending import (
    list_pending,
    remove_pending,
)
from xray_detector.infrastructure.dataset_store.store import DatasetStore
from xray_detector.ui.busy_indicator import BusyIndicator
from xray_detector.ui.capture_card import CaptureCard, Thumbnail
from xray_detector.ui.colors import (
    BORDER,
    CARD_BORDER,
    HEADER_BACKGROUND,
    MUTED_TEXT,
    PENDING_COLOR,
    SELECTED_BORDER,
    SUBTLE_TEXT,
    TEXT_DARK,
    TEXT_LIGHT,
    class_color,
)
from xray_detector.ui.flow_layout import FlowLayout
from xray_detector.ui.image_utils import bgr_to_qimage
from xray_detector.ui.settings_dialog import (
    SORT_NEWEST,
    DatasetSortSection,
    settings_button,
    sort_order,
    train_ratio,
)
from xray_detector.ui.shortcuts import (
    bind_default_action,
    bind_delete,
    mnemonic,
    with_hint,
)
from xray_detector.ui.style import button
from xray_detector.ui.variation_dialog import VariationDialog

THUMB_HEIGHT = 170
UNKNOWN_DATE = "Okänt datum"
ALL_CLASSES = "Alla klasser"
NO_MATCHES = "Inga bilder matchar filtret."
DATE_FORMAT = "yyyy-MM-dd"
HEADER_OBJECT_NAME = "captureHeader"
# kortets egen marginal är 8, så 2 här ger den syntetiska ikonen 10 px luft
# både upptill och till höger (TASK-120)
HEADER_MARGINS = (6, 2, 6, 2)
TIME_BADGE_GAP = 6
ALL_IMAGES = "Alla bilder"
ORIGINALS_ONLY = "Endast original"
SYNTHETIC_ONLY = "Endast syntetiska"
IMAGE_TYPES = (
    (None, ALL_IMAGES),
    ("original", ORIGINALS_ONLY),
    ("synthetic", SYNTHETIC_ONLY),
)
# ikonen finns färdig i rätt storlek, så korten slipper skala om den (TASK-120)
SYNTHETIC_ICON_PATH = Path(__file__).parent / "assets" / "generated-20.png"
# luften mellan utöka/återställ och exportknapparna, så grupperna syns var för sig
BUTTON_GROUP_GAP = 24


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


def _pairs(count: int) -> str:
    """'1 syntetiskt bildpar' eller '2 syntetiska bildpar' (TASK-88)."""
    if count == 1:
        return "1 syntetiskt bildpar"
    return f"{count} syntetiska bildpar"


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


def _badge(name: str, parent: QWidget) -> QLabel:
    """Klassmärke i rubrikraden, färgat med klassens färg (TASK-66)."""
    color = class_color(name)
    text_color = TEXT_DARK if color.lightness() > 140 else TEXT_LIGHT
    badge = QLabel(name, parent)
    badge.setStyleSheet(
        f"QLabel {{ background: {color.name()}; color: {text_color}; "
        "border-radius: 6px; padding: 1px 6px; font-weight: bold; }"
    )
    return badge


def _synthetic_icon(variation: dict | list, parent: QWidget) -> QLabel:
    """Ikon som visar att bildparet är syntetiskt genererat (TASK-88, TASK-120).

    Tooltipen anger vilka variationer som skapade paret, så en rotation går att
    skilja från en spegling utan att öppna datasetets metadata. En bild kan bära
    flera variationer samtidigt (TASK-106).
    """
    icon = QLabel(parent)
    icon.setPixmap(QPixmap(str(SYNTHETIC_ICON_PATH)))
    icon.setToolTip(f"Syntetisk variation: {describe(variation)}")
    return icon


def _capture_header(
    text: str,
    color: str,
    parent: QWidget,
    classes: tuple[str, ...] = (),
    synthetic: dict | list | None = None,
) -> tuple[QWidget, QLabel]:
    """Rubrikrad med tid, klassmärken och den syntetiska ikonen (TASK-66, TASK-68, TASK-88).

    Raden bär färgen och bakgrunden, så markeringen täcker både tiden och
    märkena. Texten är densamma i alla lägen, så märkena hamnar strax efter
    tidsangivelsen och kortet behåller sin storlek när fångsten markeras.
    Märkena får extra luft mot tiden men sitter tätt ihop inbördes. Den
    syntetiska ikonen ligger sist i raden, alltså i kortets övre högra hörn
    (TASK-120).
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
        layout.addWidget(_badge(name, row))
    layout.addStretch(1)
    if synthetic is not None:
        layout.addWidget(_synthetic_icon(synthetic, row))
    return row, label


def _thumbnail_pixmap(
    thumb: QImage,
    annotations: list[dict],
    source_height: int,
) -> QPixmap:
    """Tumnageln med bildens detektioner inritade (TASK-64, TASK-149).

    Bilden är redan nedskalad i arbetstråden. Ritas efter nedskalningen, så
    ramen blir lika tunn på alla bilder. Skalan är tumnagelns höjd delad med
    originalbildens, vilket gäller båda axlarna eftersom skalningen behåller
    bildförhållandet.
    """
    pixmap = QPixmap.fromImage(thumb)
    if not annotations or source_height <= 0:
        return pixmap
    scale = pixmap.height() / source_height
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen()
    pen.setWidth(2)
    for annotation in annotations:
        x, y, width, height = annotation["bbox"]
        pen.setColor(class_color(annotation["class_name"]))
        painter.setPen(pen)
        painter.drawRect(QRectF(x * scale, y * scale, width * scale, height * scale))
    painter.end()
    return pixmap


class DatasetView(QWidget):
    open_annotation_requested = Signal(object)
    status_changed = Signal(str)

    def __init__(self, config: AppConfig, dataset: DatasetStore, settings, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.dataset_store = dataset
        self.settings = settings
        # nedskalade tumnaglar per (bild-id, mtime), så en omladdning bara
        # avkodar bilder som är nya eller ändrade (TASK-149)
        self._thumb_cache: dict[tuple[int, int], QImage] = {}
        self._thumbs: list[Thumbnail] = []
        self._groups: dict[int, list[Thumbnail]] = {}
        self._group_headers: dict = {}
        self._section_headings: dict[str, QLabel] = {}
        self._section_cards: dict[str, QWidget] = {}
        self._dataset: dict | None = None
        self._pending_by_group: dict[str, object] = {}
        self._refresh_task: BackgroundTask | None = None
        self._refresh_pending = False
        self._export_task: BackgroundTask | None = None
        self._export_label = ""
        self._variation_task: BackgroundTask | None = None
        self._data: dict | None = None
        self._date_bounds_ready = False

        layout = QVBoxLayout(self)
        bar = QHBoxLayout()
        # hela raden ligger till höger, och utöka/återställ får ett eget
        # mellanrum till exportknapparna så grupperna syns var för sig (TASK-102)
        bar.addStretch(1)
        self.variation_button = button(mnemonic("Utöka med bildvariationer", "U"))
        self.variation_button.clicked.connect(self._on_add_variations)
        bar.addWidget(self.variation_button)
        self.reset_button = button(mnemonic("Återställ till original", "R"))
        self.reset_button.clicked.connect(self._on_reset_synthetic)
        bar.addWidget(self.reset_button)
        bar.addSpacing(BUTTON_GROUP_GAP)
        self.export_coco_button = button(mnemonic("Exportera COCO", "E"))
        self.export_coco_button.clicked.connect(self._on_export_coco)
        bar.addWidget(self.export_coco_button)
        self.export_yolo_button = button(mnemonic("Exportera YOLO", "Y"))
        self.export_yolo_button.clicked.connect(self._on_export_yolo)
        bar.addWidget(self.export_yolo_button)
        self.delete_button = button(mnemonic("Ta bort markerade", "B"))
        self.delete_button.clicked.connect(self._on_delete)
        bar.addWidget(self.delete_button)
        # klasslistan är datasetets egen, så rensningen står som en egen grupp (TASK-109)
        bar.addSpacing(BUTTON_GROUP_GAP)
        self.unused_classes_button = button(mnemonic("Ta bort oanvända klasser", "k"))
        self.unused_classes_button.clicked.connect(self._on_remove_unused_classes)
        bar.addWidget(self.unused_classes_button)
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
        filters.addWidget(QLabel("Bildtyp:"))
        self.type_combo = QComboBox()
        for key, label in IMAGE_TYPES:
            self.type_combo.addItem(label, key)
        self.type_combo.currentIndexChanged.connect(self._on_filter_changed)
        filters.addWidget(self.type_combo)
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
        # Enter öppnar det markerade bildparet och Del tar bort det (TASK-116)
        bind_default_action(self, self._on_open_selected)
        bind_delete(self, self._on_delete)
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
        """Läser datasetet och dekoder tumnaglarna utan att röra widgets (TASK-40, TASK-149).

        Bildavkodningen är den dyra delen: mätt 826 av 870 ms för 200 bilder.
        Bilderna skalas ner till tumnagelhöjd redan här, så minnet räcker till
        hela datasetet i stället för att varje bild ligger i full upplösning
        till en 170 px tumnagel. Cachen nycklas på (bild-id, mtime), så en
        omladdning efter en sparad annotering bara avkodar nya och ändrade
        bilder. QImage får skapas utanför GUI-tråden, QPixmap får det inte.
        """
        pending = list_pending(self.config.data_dir)
        dataset = self.dataset_store.load_dataset()
        images_dir = self.dataset_store.images_dir
        decoded: dict[int, QImage] = {}
        cache: dict[tuple[int, int], QImage] = {}
        for image in dataset["images"]:
            path = images_dir / image["file_name"]
            try:
                mtime = path.stat().st_mtime_ns
            except OSError:
                mtime = 0
            key = (image["id"], mtime)
            thumb = self._thumb_cache.get(key)
            if thumb is None:
                full = QImage(str(path))
                if full.isNull():
                    continue
                thumb = full.scaledToHeight(
                    THUMB_HEIGHT, Qt.TransformationMode.SmoothTransformation
                )
            cache[key] = thumb
            decoded[image["id"]] = thumb
        # bara bilder som finns kvar i datasetet behåller sin tumnagel
        self._thumb_cache = cache
        return {"dataset": dataset, "images": decoded, "pending": pending}

    def _on_load_failed(self, message: str) -> None:
        self.status_changed.emit(f"Kunde inte läsa datasetet: {message}")

    def _on_refresh_finished(self) -> None:
        self._refresh_task = None
        self._update_busy()
        if self._refresh_pending:
            self._refresh_pending = False
            self.refresh()

    def _update_busy(self) -> None:
        """Stänger indikatorn först när ingen omladdning, export eller utökning pågår."""
        if (
            self._refresh_task is None
            and self._export_task is None
            and self._variation_task is None
        ):
            self.busy.stop()

    def wait_for_refresh(self, timeout_ms: int = 10000) -> None:
        """Väntar in en pågående omladdning (tester och stängning)."""
        while self._refresh_task is not None:
            if not self._refresh_task.wait(timeout_ms):
                return

    def _on_export_coco(self) -> None:
        self._start_export(
            "COCO", lambda export_root: export_coco(self.dataset_store, export_root)
        )

    def _on_export_yolo(self) -> None:
        """YOLO-exporten delar train/val med träningsvyns andel (TASK-72)."""
        ratio = train_ratio(self.settings)
        self._start_export(
            "YOLO",
            lambda export_root: export_yolo(self.dataset_store, export_root, ratio),
        )

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

    def _on_add_variations(self) -> None:
        """Utökar datasetet med de variationer dialogen valt (TASK-88).

        Dialogen räknar ut antalet bildpar innan den genomförs, och själva
        bildarbetet ligger i en arbetstråd eftersom varje variation skrivs som
        en egen bildfil.
        """
        if self._variation_task is not None:
            return
        pairs = self._original_pairs()
        if not pairs:
            self.status_changed.emit("Det finns inga originalbilder att variera")
            return
        dialog = VariationDialog(pairs, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        settings = dialog.settings()
        if settings.total == 0:
            return
        self.busy.start("Skapar bildvariationer...")
        self._set_variation_enabled(False)
        task = BackgroundTask(lambda: self.dataset_store.add_variations(settings))
        task.succeeded.connect(self._on_variations_done)
        task.failed.connect(self._on_variations_failed)
        task.finished.connect(self._on_variations_finished)
        self._variation_task = task
        task.start()

    def _on_variations_done(self, added: int) -> None:
        self.status_changed.emit(f"Lade till {_pairs(added)} i datasetet")
        self.refresh()

    def _on_variations_failed(self, message: str) -> None:
        self.status_changed.emit(f"Kunde inte skapa bildvariationer: {message}")

    def _on_variations_finished(self) -> None:
        self._variation_task = None
        self._update_busy()
        self._set_variation_enabled(True)

    def wait_for_variations(self, timeout_ms: int = 10000) -> None:
        """Väntar in en pågående utökning (tester och stängning)."""
        if self._variation_task is not None:
            self._variation_task.wait(timeout_ms)

    def _set_variation_enabled(self, enabled: bool) -> None:
        self.variation_button.setEnabled(enabled)
        self.reset_button.setEnabled(enabled)

    def _on_reset_synthetic(self) -> None:
        """Raderar alla syntetiska bilder så bara originalen är kvar (TASK-88)."""
        pairs = self._synthetic_pairs()
        if not pairs:
            self.status_changed.emit("Det finns inga syntetiska bilder att ta bort")
            return
        answer = QMessageBox.question(
            self,
            "Återställ till original",
            f"Ta bort {_pairs(pairs)}? Originalbilderna ligger kvar.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.dataset_store.delete_synthetic()
        self.status_changed.emit(f"Tog bort {_pairs(pairs)} från datasetet")
        self.refresh()

    def _original_pairs(self) -> int:
        """Antal bildpar som bara innehåller originalbilder (TASK-88)."""
        return self._pair_count(synthetic=False)

    def _synthetic_pairs(self) -> int:
        """Antal bildpar som är syntetiskt genererade (TASK-88)."""
        return self._pair_count(synthetic=True)

    def _pair_count(self, synthetic: bool) -> int:
        """Antalet fångstgrupper av den ena eller andra typen i det lästa datasetet."""
        if self._dataset is None:
            return 0
        return len(
            {
                capture_group(image)
                for image in self._dataset["images"]
                if bool(image.get("synthetic")) is synthetic
            }
        )

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
        dataset = data["dataset"]
        self._dataset = dataset
        self.variation_button.setEnabled(self._original_pairs() > 0)
        self.reset_button.setEnabled(self._synthetic_pairs() > 0)
        annotations_by_image: dict[int, list[dict]] = {
            image["id"]: image["annotations"] for image in dataset["images"]
        }

        groups: dict[int, list[dict]] = {}
        for image in dataset["images"]:
            key = image.get("group") or image["id"]
            groups.setdefault(key, []).append(image)

        selected_type = self.type_combo.currentData()
        by_date: dict[str, list] = {}
        for key in sorted(groups, reverse=newest_first):
            images = sorted(groups[key], key=lambda img: img["id"])
            if not self._matches_type(images, selected_type):
                continue
            stamp = _format_timestamp(images[0].get("captured")) or _mtime_timestamp(
                self.dataset_store.images_dir / images[0]["file_name"]
            )
            by_date.setdefault(stamp[:10], []).append((key, images, stamp))

        self._sync_filters(
            self._filter_classes(dataset, data["pending"]),
            self._capture_days(data, by_date),
        )
        if selected_type != "synthetic":
            # osparade fångster är alltid original, så de göms med syntetiska
            self._add_pending_section(data["pending"], newest_first)
        if not dataset["images"]:
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
                    ann["class_name"]
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

    def _filter_classes(self, dataset: dict, pending) -> list[str]:
        """Klasserna som går att filtrera på: datasetets och de osparades (TASK-67)."""
        names = list(dataset["classes"])
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

    @staticmethod
    def _matches_type(images: list[dict], selected: str | None) -> bool:
        """Om fångsten är syntetisk eller ett original (TASK-88).

        Ett bildpar är syntetiskt när bilderna i det är det, så filtret gäller
        hela paret och korten delas aldrig upp.
        """
        if selected is None:
            return True
        synthetic = any(image.get("synthetic") for image in images)
        return synthetic if selected == "synthetic" else not synthetic

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
        color = PENDING_COLOR if pending else SUBTLE_TEXT
        heading.setStyleSheet(
            f"font-weight: bold; color: {color}; "
            f"border-bottom: 1px solid {BORDER}; padding-bottom: 2px;"
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
        decoded: dict,
    ) -> None:
        """Ett kort per fångst: tid, klassmärken och bildparet (TASK-42, TASK-66)."""
        classes = tuple(
            sorted(
                {
                    ann["class_name"]
                    for img in images
                    for ann in annotations_by_image.get(img["id"], [])
                }
            )
        )
        variation = next(
            (img.get("variation") or {} for img in images if img.get("synthetic")),
            None,
        )
        time_label = stamp[11:] if stamp else f"Fångst {key}"
        card = CaptureCard(key)
        card.setFrameShape(QFrame.Shape.Box)
        card.setStyleSheet(_card_style(CARD_BORDER))
        card.clicked.connect(self._on_card_clicked)
        header, header_label = _capture_header(
            time_label, MUTED_TEXT, card, classes, variation
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
                decoded[image["id"]], annotations, int(image.get("height") or 0)
            )
            thumb = Thumbnail(image["id"], key, pixmap)
            thumb.clicked.connect(self._on_thumb_clicked)
            thumb.double_clicked.connect(self._on_thumb_double_clicked)
            row.addWidget(thumb)
            self._thumbs.append(thumb)
            self._groups.setdefault(key, []).append(thumb)
        inner.addLayout(row)
        cards.addWidget(card)

    def _add_pending_section(self, captures, newest_first: bool = True) -> None:
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
            card.setStyleSheet(_card_style(PENDING_COLOR, dashed=True))
            card.clicked.connect(self._on_card_clicked)
            header, header_label = _capture_header(title, PENDING_COLOR, card, classes)
            self._group_headers[capture.group_id] = (header_label, card)
            inner = QVBoxLayout(card)
            inner.setContentsMargins(8, 8, 8, 8)
            inner.setSpacing(4)
            inner.addWidget(header)
            row = QHBoxLayout()
            row.setSpacing(4)
            for stream_frame in capture.frames:
                image = bgr_to_qimage(stream_frame.frame).scaledToHeight(
                    THUMB_HEIGHT, Qt.TransformationMode.SmoothTransformation
                )
                pixmap = QPixmap.fromImage(image)
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
            row.setStyleSheet(_header_style(HEADER_BACKGROUND, SELECTED_BORDER))
            header.setStyleSheet(_header_text_style(HEADER_BACKGROUND))
            frame.setStyleSheet(_card_style(SELECTED_BORDER))
        elif pending:
            row.setStyleSheet(_header_style(PENDING_COLOR))
            header.setStyleSheet(_header_text_style(PENDING_COLOR))
            frame.setStyleSheet(_card_style(PENDING_COLOR, dashed=True))
        else:
            row.setStyleSheet(_header_style(MUTED_TEXT))
            header.setStyleSheet(_header_text_style(MUTED_TEXT))
            frame.setStyleSheet(_card_style(CARD_BORDER))

    def _selected_groups(self) -> list:
        """Fångstgrupperna som har minst en markerad bild, i listordning (TASK-73)."""
        return list(
            dict.fromkeys(thumb.group_id for thumb in self._thumbs if thumb.selected)
        )

    def _update_delete_button(self) -> None:
        """Antalet markerade bildpar; bilderna hanteras alltid i par (TASK-73)."""
        count = len(self._selected_groups())
        label = f"Ta bort markerade ({count})" if count else "Ta bort markerade"
        self.delete_button.setText(with_hint(mnemonic(label, "B"), "Del"))
        self.delete_button.setEnabled(count > 0)

    def _on_open_selected(self) -> None:
        """Enter öppnar det markerade bildparet för annotering (TASK-116).

        Samma väg som dubbelklicket. Bara ett markerat bildpar öppnas: Enter ska
        inte välja bland flera, och utan markering finns inget att öppna.
        """
        groups = self._selected_groups()
        if len(groups) != 1:
            return
        thumb = next(thumb for thumb in self._thumbs if thumb.group_id == groups[0])
        self._on_thumb_double_clicked(thumb)

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
            entry = next(
                img for img in self._dataset["images"] if img["id"] == member.image_id
            )
            frame = cv2.imread(str(self.dataset_store.images_dir / entry["file_name"]))
            if frame is None:
                continue
            detections = []
            for annotation in entry["annotations"]:
                x, y, w, h = annotation["bbox"]
                detections.append(
                    Detection(x1=float(x), y1=float(y), x2=float(x + w), y2=float(y + h),
                             class_name=annotation["class_name"], confidence=1.0)
                )
            frames.append(
                StreamFrame(source_id=f"img{entry['id']}", frame=frame,
                             detections=detections, source_label=entry["file_name"],
                             dataset_id=entry["id"])
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
        # bilderna tas alltid bort i par, så antalet är fångstgrupper (TASK-73)
        count = len(self._selected_groups())
        answer = QMessageBox.question(
            self,
            "Ta bort bildpar",
            f"Ta bort {count} bildpar med tillhörande annoteringar? Det går inte att ångra.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        if ids:
            self.dataset_store.delete_images(ids)
        for group_id in pending_ids:
            remove_pending(self.config.data_dir, group_id)
        self.status_changed.emit(f"Tog bort {count} bildpar från datasetet")
        self.refresh()

    def _on_remove_unused_classes(self) -> None:
        """Rensar klasslistan till de klasser som finns annoterade (TASK-109)."""
        unused = self.dataset_store.unused_classes()
        if not unused:
            self.status_changed.emit("Alla klasser i datasetet används")
            return
        answer = QMessageBox.question(
            self,
            "Ta bort oanvända klasser",
            f"Ta bort {len(unused)} oanvända klasser ur datasetets klasslista?\n\n"
            + ", ".join(unused),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        removed = self.dataset_store.remove_unused_classes()
        self.status_changed.emit(f"Tog bort {len(removed)} oanvända klasser")
        self.refresh()
