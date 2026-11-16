"""Dialog för att utöka datasetet med syntetiska bildvariationer (TASK-88).

Varje variationstyp har ett antal variationer per originalbild och en styrka
för hur mycket som får ändras. Vändningen har inget antal: de två
riktningarna är var sin variation. Dialogen räknar ut hur många bildpar
utökningen ger innan den genomförs, så antalet syns innan datasetet ändras.
"""

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from xray_detector.domain.dataset import VariationSettings
from xray_detector.ui.style import FormCard, apply_metrics

MAX_COUNT = 20
MAX_DEGREES = 360
MAX_PERCENT = 100
DEFAULT_DEGREES = 360
DEFAULT_SCALE_PERCENT = 50
DEFAULT_COLOR_PERCENT = 20
NO_VARIATIONS = "Ange minst en variation."
# dialogen blir annars bara så bred som fälten, och då radbryts summeringen hårt
MIN_WIDTH = 380


def _count(maximum: int, suffix: str = "") -> QSpinBox:
    """Heltalsfält för antal variationer eller för styrkan i procent och grader."""
    widget = QSpinBox()
    widget.setRange(0, maximum)
    if suffix:
        widget.setSuffix(suffix)
    return widget


class VariationDialog(QDialog):
    """Antal och styrka per variationstyp; Utöka lämnar inställningarna.

    Avbryt stänger dialogen utan att något ändras, eftersom datasetet först
    skrivs när vyn genomför utökningen med settings().
    """

    def __init__(self, pairs: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Utöka med bildvariationer")
        self.setMinimumWidth(MIN_WIDTH)
        self.pairs = pairs
        layout = QVBoxLayout(self)

        rotation = FormCard("Rotation", self)
        self.rotation_count = _count(MAX_COUNT)
        self.rotation_degrees = _count(MAX_DEGREES, " °")
        self.rotation_degrees.setValue(DEFAULT_DEGREES)
        rotation.form.addRow(QLabel("Antal variationer:"), self.rotation_count)
        rotation.form.addRow(QLabel("Vinkel ±:"), self.rotation_degrees)
        layout.addWidget(rotation)

        flip = FormCard("Vändning", self)
        self.flip_horizontal = QCheckBox("Horisontellt")
        self.flip_vertical = QCheckBox("Vertikalt")
        flip.form.addRow(self.flip_horizontal)
        flip.form.addRow(self.flip_vertical)
        layout.addWidget(flip)

        scale = FormCard("Storlek", self)
        self.scale_count = _count(MAX_COUNT)
        self.scale_percent = _count(MAX_PERCENT, " %")
        self.scale_percent.setValue(DEFAULT_SCALE_PERCENT)
        scale.form.addRow(QLabel("Antal variationer:"), self.scale_count)
        scale.form.addRow(QLabel("Ändring ±:"), self.scale_percent)
        layout.addWidget(scale)

        color = FormCard("Färg", self)
        self.color_count = _count(MAX_COUNT)
        self.color_percent = _count(MAX_PERCENT, " %")
        self.color_percent.setValue(DEFAULT_COLOR_PERCENT)
        color.form.addRow(QLabel("Antal variationer:"), self.color_count)
        color.form.addRow(QLabel("Ändring ±:"), self.color_percent)
        layout.addWidget(color)

        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        hint = QLabel(
            "Variationerna skapas från originalbilderna och läggs till som egna "
            "bildpar. De kan tas bort igen med Återställ till original."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #888;")
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
            self.rotation_count,
            self.rotation_degrees,
            self.scale_count,
            self.scale_percent,
            self.color_count,
            self.color_percent,
        ):
            widget.valueChanged.connect(self._update_summary)
        for box in (self.flip_horizontal, self.flip_vertical):
            box.toggled.connect(self._update_summary)
        self._update_summary()

    def settings(self) -> VariationSettings:
        """Inställningarna som utökningen genomförs med."""
        return VariationSettings(
            rotation_count=self.rotation_count.value(),
            rotation_degrees=float(self.rotation_degrees.value()),
            flip_horizontal=self.flip_horizontal.isChecked(),
            flip_vertical=self.flip_vertical.isChecked(),
            scale_count=self.scale_count.value(),
            scale_percent=float(self.scale_percent.value()),
            color_count=self.color_count.value(),
            color_percent=float(self.color_percent.value()),
        )

    def _update_summary(self, *_args) -> None:
        """Summeringen och Utöka följer valen, så antalet syns före utökningen."""
        total = self.settings().total
        self.extend_button.setEnabled(total > 0)
        if total == 0:
            self.summary.setText(NO_VARIATIONS)
            return
        self.summary.setText(
            f"{total} variationer per bildpar ger {total * self.pairs} nya "
            f"bildpar från {self.pairs} original."
        )
