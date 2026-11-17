"""Inställningsdelar (TASK-43).

Sektionerna som bygger inställningsfliken och vyernas dialoger, dialogen och
knappen som öppnar den. Applikationens globala inställningar ligger i
settings_view.py, som komponerar ThemeSection härifrån.
"""

from datetime import time

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from xray_detector.domain.training import (
    NIGHT_END_DEFAULT,
    NIGHT_END_KEY,
    NIGHT_START_DEFAULT,
    NIGHT_START_KEY,
    format_clock,
    parse_clock,
)
from xray_detector.ui.badge import (
    HIDE_FRAMES_KEY,
    SHOW_FRAMES_KEY,
    SWAP_FRAMES_KEY,
    badge_delays,
    badge_swap_frames,
)
from xray_detector.ui.shortcuts import mnemonic
from xray_detector.ui.style import FormCard, apply_metrics, button
from xray_detector.ui.theme import THEMES, apply_theme, current_theme

GEAR_COLOR = "#8a8a8a"
SORT_KEY = "dataset/sort_order"
SORT_NEWEST = "newest"
SORT_OLDEST = "oldest"
SORT_ORDERS = {SORT_NEWEST: "Nyast först", SORT_OLDEST: "Äldst först"}
NO_CLASSES = "Inga klasser valda – ingen detektion körs"
TRAIN_RATIO_KEY = "training/train_ratio"
TRAIN_RATIO_DEFAULT = 80
CLASS_COLUMNS = 5
CLASS_LIST_MAX_HEIGHT = 420


def sort_order(settings) -> str:
    """Vald sortering i datasetvyn; nyast först när inget val sparats (TASK-56)."""
    value = settings.value(SORT_KEY, SORT_NEWEST, type=str)
    return value if value in SORT_ORDERS else SORT_NEWEST


def train_ratio(settings) -> float:
    """Andel av bildparen som hamnar i train, som 0-1 (TASK-72).

    Värdet sparas i procent så inställningen går att läsa i settings.ini, och
    kläms till 1-99 så både train och val får minst en grupp.
    """
    percent = settings.value(TRAIN_RATIO_KEY, TRAIN_RATIO_DEFAULT, type=int)
    return max(1, min(99, int(percent))) / 100.0


class ThemeSection(FormCard):
    """Temaval; gäller hela appen och visas i inställningsfliken."""

    def __init__(self, settings, parent=None) -> None:
        super().__init__("Utseende", parent)
        self.settings = settings
        form = self.form
        self.theme_combo = QComboBox()
        for key, label in THEMES.items():
            self.theme_combo.addItem(label, key)
        index = self.theme_combo.findData(current_theme())
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        form.addRow(QLabel("Tema:"), self.theme_combo)

    def _on_theme_changed(self) -> None:
        theme = self.theme_combo.currentData()
        self.settings.setValue("ui/theme", theme)
        apply_theme(QApplication.instance(), theme)


class TrainingScheduleSection(FormCard):
    """Träningsschema: nattfönster och inaktivitetsgräns (TASK-7, flyttad hit)."""

    def __init__(self, settings, parent=None) -> None:
        super().__init__("Träningsschema", parent)
        self.settings = settings
        form = self.form
        self.night_start = QSpinBox()
        self.night_start.setRange(0, 23)
        self.night_start.setValue(
            parse_clock(settings.value(NIGHT_START_KEY), NIGHT_START_DEFAULT).hour
        )
        self.night_start.valueChanged.connect(
            lambda hour: self._save_clock(hour, is_start=True)
        )
        form.addRow(QLabel("Nattfönster börjar (timme):"), self.night_start)
        self.night_end = QSpinBox()
        self.night_end.setRange(0, 23)
        self.night_end.setValue(
            parse_clock(settings.value(NIGHT_END_KEY), NIGHT_END_DEFAULT).hour
        )
        self.night_end.valueChanged.connect(
            lambda hour: self._save_clock(hour, is_start=False)
        )
        form.addRow(QLabel("Nattfönster slutar (timme):"), self.night_end)
        self.inactivity = QSpinBox()
        self.inactivity.setRange(1, 240)
        self.inactivity.setValue(
            int(settings.value("training/inactivity_minutes", 30, type=int))
        )
        self.inactivity.valueChanged.connect(
            lambda minutes: settings.setValue("training/inactivity_minutes", minutes)
        )
        form.addRow(QLabel("Inaktivitet innan träning (min):"), self.inactivity)

    def _save_clock(self, hour: int, is_start: bool) -> None:
        key = NIGHT_START_KEY if is_start else NIGHT_END_KEY
        self.settings.setValue(key, format_clock(time(hour, 0)))


class DatasetSortSection(FormCard):
    """Sortering av fångsterna i datasetvyn (TASK-56)."""

    order_changed = Signal()

    def __init__(self, settings, parent=None) -> None:
        super().__init__("Sortering", parent)
        self.settings = settings
        form = self.form
        self.order_combo = QComboBox()
        for key, label in SORT_ORDERS.items():
            self.order_combo.addItem(label, key)
        index = self.order_combo.findData(sort_order(settings))
        if index >= 0:
            self.order_combo.setCurrentIndex(index)
        self.order_combo.currentIndexChanged.connect(self._on_order_changed)
        form.addRow(QLabel("Fångster:"), self.order_combo)

    def _on_order_changed(self) -> None:
        self.settings.setValue(SORT_KEY, self.order_combo.currentData())
        self.order_changed.emit()


class BadgeSection(FormCard):
    """Fördröjningen för klassmärket i videofönstren (TASK-84).

    Märket kräver ett antal ramar i följd med klassen innan det visas och
    lika många utan innan det döljs, så en detektion nära tröskelvärdet inte
    får märket att flimra. Trögheten i platsbyten ställs in här också: den
    säkraste klassen ligger överst, men tar bara över platsen när den varit
    säkrast ett antal ramar i följd (TASK-86). Ändringar sparas direkt och
    slår igenom på båda panelerna utan att dialogen stängs.
    """

    def __init__(self, settings, on_changed, parent=None) -> None:
        super().__init__("Klassmärke", parent)
        self.settings = settings
        self.on_changed = on_changed
        form = self.form
        show_frames, hide_frames = badge_delays(settings)
        self.show_frames = QSpinBox()
        self.show_frames.setRange(1, 60)
        self.show_frames.setSuffix(" ramar")
        self.show_frames.setValue(show_frames)
        self.show_frames.valueChanged.connect(self._on_show_changed)
        form.addRow(QLabel("Visa efter:"), self.show_frames)
        self.hide_frames = QSpinBox()
        self.hide_frames.setRange(1, 120)
        self.hide_frames.setSuffix(" ramar")
        self.hide_frames.setValue(hide_frames)
        self.hide_frames.valueChanged.connect(self._on_hide_changed)
        form.addRow(QLabel("Dölj efter:"), self.hide_frames)
        self.swap_frames = QSpinBox()
        self.swap_frames.setRange(1, 120)
        self.swap_frames.setSuffix(" ramar")
        self.swap_frames.setValue(badge_swap_frames(settings))
        self.swap_frames.valueChanged.connect(self._on_swap_changed)
        form.addRow(QLabel("Byt plats efter:"), self.swap_frames)
        hint = QLabel(
            "Antal ramar i följd som klassen måste detekteras i innan märket "
            "visas, respektive saknas i innan det döljs. Platsbytet kräver "
            "lika många ramar i följd där en annan klass är säkrare, så två "
            "klasser med nästan samma sannolikhet inte byter plats ofta."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #888;")
        form.addRow(hint)

    def _on_show_changed(self, frames: int) -> None:
        self.settings.setValue(SHOW_FRAMES_KEY, frames)
        self.on_changed()

    def _on_hide_changed(self, frames: int) -> None:
        self.settings.setValue(HIDE_FRAMES_KEY, frames)
        self.on_changed()

    def _on_swap_changed(self, frames: int) -> None:
        self.settings.setValue(SWAP_FRAMES_KEY, frames)
        self.on_changed()


class ClassFilterSection(QGroupBox):
    """Klasserna som vald modell ska detektera (TASK-53).

    Klasslistan följer modellen, så sektionen byggs om varje gång dialogen
    öppnas. Bortvalda klasser sparas av vyn, inte här. En modell kan ha
    hundratals klasser (COCO-80), så rutorna ligger i ett rutnät i en
    rullista i stället för en enda lång kolumn (TASK-75). Knappen ovanför
    listan växlar mellan alla och inga klasser (TASK-77).
    """

    def __init__(self, class_names, disabled, on_changed, parent=None) -> None:
        super().__init__("Klasser", parent)
        self.on_changed = on_changed
        self.checkboxes: dict[str, QCheckBox] = {}
        layout = QVBoxLayout(self)
        if not class_names:
            layout.addWidget(QLabel("Klasserna läses när modellen har laddats."))
            return
        self.toggle_button = button(mnemonic("Markera alla", "M"))
        self.toggle_button.clicked.connect(self._toggle_all)
        row = QHBoxLayout()
        row.addWidget(self.toggle_button)
        row.addStretch(1)
        layout.addLayout(row)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setMaximumHeight(CLASS_LIST_MAX_HEIGHT)
        content = QWidget()
        grid = QGridLayout(content)
        grid.setContentsMargins(0, 0, 0, 0)
        for index, name in enumerate(class_names):
            box = QCheckBox(name)
            box.setChecked(name not in disabled)
            box.toggled.connect(self._on_toggled)
            grid.addWidget(box, index // CLASS_COLUMNS, index % CLASS_COLUMNS)
            self.checkboxes[name] = box
        self.scroll.setWidget(content)
        # rullistan är så bred att alla kolumner syns även när höjden rullar
        self.scroll.setMinimumWidth(
            content.sizeHint().width()
            + self.scroll.verticalScrollBar().sizeHint().width()
            + 2 * self.scroll.frameWidth()
        )
        layout.addWidget(self.scroll)
        self.warning = QLabel(NO_CLASSES)
        self.warning.setStyleSheet("color: #c33;")
        layout.addWidget(self.warning)
        self._update_toggle_text()
        self._update_warning()

    def selected(self) -> list[str]:
        return [name for name, box in self.checkboxes.items() if box.isChecked()]

    def _toggle_all(self) -> None:
        """Markerar alla klasser, eller avmarkerar alla när alla redan är valda.

        Kryssrutornas signaler blockeras under omslaget, så vyn får ett enda
        besked och detektionen startas om en gång i stället för en gång per
        klass (TASK-77).
        """
        target = len(self.selected()) < len(self.checkboxes)
        for box in self.checkboxes.values():
            box.blockSignals(True)
            box.setChecked(target)
            box.blockSignals(False)
        self._update_toggle_text()
        self._update_warning()
        self.on_changed(self.selected())

    def _on_toggled(self, *_args) -> None:
        self._update_toggle_text()
        self._update_warning()
        self.on_changed(self.selected())

    def _update_toggle_text(self) -> None:
        """Etiketten visar vad nästa klick gör."""
        label = "Avmarkera alla" if len(self.selected()) == len(self.checkboxes) else "Markera alla"
        self.toggle_button.setText(mnemonic(label, "M"))

    def _update_warning(self) -> None:
        self.warning.setVisible(not self.selected())


class SettingsDialog(QDialog):
    """Vyens inställningar; ändringar sparas direkt och Stäng lämnar dem orörda."""

    def __init__(self, title: str, sections: list[QWidget], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        for section in sections:
            layout.addWidget(section)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close = buttons.button(QDialogButtonBox.StandardButton.Close)
        close.setText("Stäng")
        apply_metrics(close)
        # Stäng är dialogens standardknapp, så Enter stänger den (TASK-116). Utan
        # detta blir sektionernas första knapp standardknapp och Enter utför då
        # dess åtgärd i stället, som att markera alla klasser.
        close.setDefault(True)
        for widget in self.findChildren(QPushButton):
            if widget is not close:
                widget.setAutoDefault(False)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


def gear_icon(size: int = 16) -> QIcon:
    """Kugghjul framför texten i inställningsknappen (TASK-43).

    Grå nyansen syns på både ljus och mörk palett; Qt tonar den själv när
    knappen är avstängd.
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(GEAR_COLOR))
    center = size / 2
    painter.drawEllipse(QPointF(center, center), size * 0.30, size * 0.30)
    for index in range(8):
        painter.save()
        painter.translate(center, center)
        painter.rotate(index * 45)
        painter.drawRoundedRect(
            QRectF(-size * 0.09, -size * 0.48, size * 0.18, size * 0.26),
            size * 0.05,
            size * 0.05,
        )
        painter.restore()
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
    painter.drawEllipse(QPointF(center, center), size * 0.12, size * 0.12)
    painter.end()
    return QIcon(pixmap)


def settings_button(parent: QWidget, title: str, sections=None) -> QPushButton:
    """Knapp som öppnar vyens inställningar (Alt+I, TASK-54).

    En vy utan egna inställningar får en avstängd knapp på samma plats, så
    placeringen är densamma oavsett vilken flik som är öppen.
    """
    widget = button(mnemonic("Inställningar", "I"), parent=parent)
    widget.setIcon(gear_icon())
    if sections is None:
        widget.setEnabled(False)
        widget.setToolTip("Vyn har inga egna inställningar")
        return widget
    widget.clicked.connect(
        lambda: SettingsDialog(title, sections(), parent.window()).exec()
    )
    return widget
