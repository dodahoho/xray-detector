"""Inställningsdelar (TASK-43).

Sektionerna som bygger inställningsfliken och vyernas dialoger, dialogen och
knappen som öppnar den. Applikationens globala inställningar ligger i
settings_view.py, som komponerar ThemeSection härifrån.
"""

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from xray_detector.ui.shortcuts import mnemonic
from xray_detector.ui.style import apply_metrics, button
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


class ThemeSection(QGroupBox):
    """Temaval; gäller hela appen och visas i inställningsfliken."""

    def __init__(self, settings, parent=None) -> None:
        super().__init__("Utseende", parent)
        self.settings = settings
        form = QFormLayout(self)
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


class TrainingScheduleSection(QGroupBox):
    """Träningsschema: nattfönster och inaktivitetsgräns (TASK-7, flyttad hit)."""

    def __init__(self, settings, parent=None) -> None:
        super().__init__("Träningsschema", parent)
        self.settings = settings
        form = QFormLayout(self)
        self.night_start = QSpinBox()
        self.night_start.setRange(0, 23)
        self.night_start.setValue(
            int(settings.value("training/night_start_hour", 23, type=int))
        )
        self.night_start.valueChanged.connect(
            lambda hour: self._save_clock(hour, is_start=True)
        )
        form.addRow(QLabel("Nattfönster börjar (timme):"), self.night_start)
        self.night_end = QSpinBox()
        self.night_end.setRange(0, 23)
        self.night_end.setValue(
            int(settings.value("training/night_end_hour", 5, type=int))
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
        key = "training/night_start" if is_start else "training/night_end"
        self.settings.setValue(f"{key}_hour", hour)
        self.settings.setValue(key, f"{hour:02d}:00")


class TrainValSplitSection(QGroupBox):
    """Andel av datasetet som används till träning respektive validering (TASK-72).

    Delningen sker per fångstgrupp, så andelen räknas i bildpar: ett bildpar
    hamnar alltid i sin helhet i train eller i val.
    """

    ratio_changed = Signal()

    def __init__(self, settings, parent=None) -> None:
        super().__init__("Train/val-delning", parent)
        self.settings = settings
        form = QFormLayout(self)
        self.ratio = QSpinBox()
        self.ratio.setRange(1, 99)
        self.ratio.setSuffix(" %")
        self.ratio.setValue(round(train_ratio(settings) * 100))
        self.ratio.valueChanged.connect(self._on_ratio_changed)
        form.addRow(QLabel("Andel till train:"), self.ratio)
        hint = QLabel("Resten används till validering. Delningen sker per bildpar.")
        hint.setStyleSheet("color: #888;")
        form.addRow(hint)

    def _on_ratio_changed(self, percent: int) -> None:
        self.settings.setValue(TRAIN_RATIO_KEY, percent)
        self.ratio_changed.emit()


class DatasetSortSection(QGroupBox):
    """Sortering av fångsterna i datasetvyn (TASK-56)."""

    order_changed = Signal()

    def __init__(self, settings, parent=None) -> None:
        super().__init__("Sortering", parent)
        self.settings = settings
        form = QFormLayout(self)
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


class ClassFilterSection(QGroupBox):
    """Klasserna som vald modell ska detektera (TASK-53).

    Klasslistan följer modellen, så sektionen byggs om varje gång dialogen
    öppnas. Bortvalda klasser sparas av vyn, inte här. En modell kan ha
    hundratals klasser (COCO-80), så rutorna ligger i ett rutnät i en
    rullista i stället för en enda lång kolumn (TASK-75).
    """

    def __init__(self, class_names, disabled, on_changed, parent=None) -> None:
        super().__init__("Klasser", parent)
        self.on_changed = on_changed
        self.checkboxes: dict[str, QCheckBox] = {}
        layout = QVBoxLayout(self)
        if not class_names:
            layout.addWidget(QLabel("Klasserna läses när modellen har laddats."))
            return
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
        self._update_warning()

    def selected(self) -> list[str]:
        return [name for name, box in self.checkboxes.items() if box.isChecked()]

    def _on_toggled(self, *_args) -> None:
        self._update_warning()
        self.on_changed(self.selected())

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
