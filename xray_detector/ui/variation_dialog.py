"""Dialog för att utöka datasetet med syntetiska bildvariationer (TASK-88, TASK-106, TASK-117).

Kombinationsläget ställs först, sedan vilka variationstyper som ska användas
och hur mycket de får ändra. En typ är avstängd tills dess kryssruta är satt,
och då är även typens fält avstängda. Antalet variationer per bildpar är ett
underval till kombinationen och gäller bara när en bild får flera typer; en
bild per variationstyp ger i stället en bild per aktiv typ. Dialogen räknar ut
hur många bildpar utökningen ger innan den genomförs.
"""

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from xray_detector.domain.dataset import MODE_PER_TYPE, MODES, VariationSettings
from xray_detector.infrastructure.dataset_store.augment import MAX_SCALE, MIN_SCALE
from xray_detector.ui.colors import MUTED_TEXT
from xray_detector.ui.style import FormCard, apply_metrics

MAX_COUNT = 20
MAX_DEGREES = 360
MAX_PERCENT = 100
# storleken kläms i augment.py till MIN_SCALE..MAX_SCALE, så procenttalen
# motsvarar den spännvidden: en bild kan växa mer än den kan krympa (TASK-117)
MAX_SCALE_UP_PERCENT = round((MAX_SCALE - 1) * 100)
MAX_SCALE_DOWN_PERCENT = round((1 - MIN_SCALE) * 100)
DEFAULT_COUNT = 1
DEFAULT_DEGREES = 360
DEFAULT_SCALE_PERCENT = 50
DEFAULT_COLOR_PERCENT = 20
NO_VARIATIONS = "Aktivera minst en variationstyp."
MODE_HINT = (
    "En per variationstyp ger ett bildpar per vald typ. Alla valda variationer "
    "lägger alla typer i samma bild. Slumpvisa kombinationer väljer en "
    "slumpmässig delmängd per bild."
)
# dialogen blir annars bara så bred som fälten, och då radbryts summeringen hårt
MIN_WIDTH = 380
# undervalet ligger indraget under valet det hör till
SUB_OPTION_INDENT = 16


def _count(maximum: int, suffix: str = "") -> QSpinBox:
    """Heltalsfält för antal bilder eller för styrkan i procent och grader."""
    widget = QSpinBox()
    widget.setRange(0, maximum)
    if suffix:
        widget.setSuffix(suffix)
    return widget


def _sub_option(label: str, field: QWidget) -> QWidget:
    """Rad indragen under valet den hör till, med etiketten före fältet."""
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(SUB_OPTION_INDENT, 0, 0, 0)
    layout.addWidget(QLabel(label))
    layout.addWidget(field)
    return row


def _type_card(title: str, parent: QWidget) -> FormCard:
    """Kort vars rubrik är en kryssruta; Qt stänger av fälten när den är av."""
    card = FormCard(title, parent)
    card.setCheckable(True)
    card.setChecked(False)
    return card


class VariationDialog(QDialog):
    """Kombination, antal och typval; Utöka lämnar inställningarna.

    Avbryt stänger dialogen utan att något ändras, eftersom datasetet först
    skrivs när vyn genomför utökningen med settings().
    """

    def __init__(self, pairs: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Utöka med bildvariationer")
        self.setMinimumWidth(MIN_WIDTH)
        self.pairs = pairs
        layout = QVBoxLayout(self)

        scope = FormCard("Omfattning", self)
        self.mode_combo = QComboBox()
        for key, label in MODES.items():
            self.mode_combo.addItem(label, key)
        scope.form.addRow(QLabel("Kombination:"), self.mode_combo)
        mode_hint = QLabel(MODE_HINT)
        mode_hint.setWordWrap(True)
        mode_hint.setStyleSheet(f"color: {MUTED_TEXT};")
        scope.form.addRow(mode_hint)
        # antalet är ett underval till kombinationen: det gäller bara när en
        # bild får flera typer, inte när varje typ ger en egen bild (TASK-117)
        self.count = _count(MAX_COUNT)
        self.count.setValue(DEFAULT_COUNT)
        self.count_row = _sub_option("Variationer per bildpar:", self.count)
        scope.form.addRow(self.count_row)
        layout.addWidget(scope)

        self.rotation = _type_card("Rotation", self)
        self.rotation_degrees = _count(MAX_DEGREES, " °")
        self.rotation_degrees.setValue(DEFAULT_DEGREES)
        self.rotation.form.addRow(QLabel("Vinkel ±:"), self.rotation_degrees)
        layout.addWidget(self.rotation)

        self.flip = _type_card("Vändning", self)
        self.flip_horizontal = QCheckBox("Horisontellt")
        self.flip_horizontal.setChecked(True)
        self.flip_vertical = QCheckBox("Vertikalt")
        self.flip_vertical.setChecked(True)
        self.flip.form.addRow(self.flip_horizontal)
        self.flip.form.addRow(self.flip_vertical)
        layout.addWidget(self.flip)

        self.scale = _type_card("Storlek", self)
        self.scale_up_percent = _count(MAX_SCALE_UP_PERCENT, " %")
        self.scale_up_percent.setValue(DEFAULT_SCALE_PERCENT)
        self.scale.form.addRow(QLabel("Öka:"), self.scale_up_percent)
        self.scale_down_percent = _count(MAX_SCALE_DOWN_PERCENT, " %")
        self.scale_down_percent.setValue(DEFAULT_SCALE_PERCENT)
        self.scale.form.addRow(QLabel("Minska:"), self.scale_down_percent)
        layout.addWidget(self.scale)

        self.color = _type_card("Färg", self)
        self.color_percent = _count(MAX_PERCENT, " %")
        self.color_percent.setValue(DEFAULT_COLOR_PERCENT)
        self.color.form.addRow(QLabel("Ändring ±:"), self.color_percent)
        layout.addWidget(self.color)

        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        hint = QLabel(
            "Variationerna skapas från originalbilderna och läggs till som egna "
            "bildpar. De kan tas bort igen med Återställ till original."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {MUTED_TEXT};")
        layout.addWidget(hint)

        buttons = QDialogButtonBox()
        self.extend_button = buttons.addButton(
            "Utöka", QDialogButtonBox.ButtonRole.AcceptRole
        )
        cancel = buttons.addButton("Avbryt", QDialogButtonBox.ButtonRole.RejectRole)
        apply_metrics(self.extend_button)
        apply_metrics(cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        for widget in (
            self.count,
            self.rotation_degrees,
            self.scale_up_percent,
            self.scale_down_percent,
            self.color_percent,
        ):
            widget.valueChanged.connect(self._update_summary)
        for card in (self.rotation, self.flip, self.scale, self.color):
            card.toggled.connect(self._update_summary)
        for box in (self.flip_horizontal, self.flip_vertical):
            box.toggled.connect(self._update_summary)
        self.mode_combo.currentIndexChanged.connect(self._update_mode)
        self._update_mode()

    def settings(self) -> VariationSettings:
        """Inställningarna som utökningen genomförs med."""
        return VariationSettings(
            count=self.count.value(),
            mode=self.mode_combo.currentData(),
            rotation=self.rotation.isChecked(),
            rotation_degrees=float(self.rotation_degrees.value()),
            flip_horizontal=self.flip.isChecked() and self.flip_horizontal.isChecked(),
            flip_vertical=self.flip.isChecked() and self.flip_vertical.isChecked(),
            scale=self.scale.isChecked(),
            scale_up_percent=float(self.scale_up_percent.value()),
            scale_down_percent=float(self.scale_down_percent.value()),
            color=self.color.isChecked(),
            color_percent=float(self.color_percent.value()),
        )

    def _update_mode(self, *_args) -> None:
        """Antalet är bara valbart när en bild får flera typer (TASK-117)."""
        self.count_row.setEnabled(self.mode_combo.currentData() != MODE_PER_TYPE)
        self._update_summary()

    def _update_summary(self, *_args) -> None:
        """Summeringen och Utöka följer valen, så antalet syns före utökningen."""
        settings = self.settings()
        total = settings.total
        self.extend_button.setEnabled(total > 0)
        if total == 0:
            self.summary.setText(NO_VARIATIONS)
            return
        if settings.mode == MODE_PER_TYPE:
            self.summary.setText(
                f"En bild per variationstyp ger {total * self.pairs} nya bildpar "
                f"från {self.pairs} original."
            )
            return
        self.summary.setText(
            f"{total} variationer per bildpar ger {total * self.pairs} nya "
            f"bildpar från {self.pairs} original."
        )
