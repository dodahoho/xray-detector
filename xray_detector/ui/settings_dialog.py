"""Inställningar per flik (TASK-43).

Inställningsfliken är borta. Varje vy har en inställningsknapp som öppnar de
inställningar som hör till vyn. Temat gäller hela appen och ligger därför i en
egen sektion som är märkt som global i varje fliks dialog.
"""

from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from xray_detector.ui.shortcuts import mnemonic
from xray_detector.ui.theme import THEMES, apply_theme, current_theme


class ThemeSection(QGroupBox):
    """Temaval; gäller hela appen, inte bara fliken (TASK-43)."""

    def __init__(self, settings, parent=None) -> None:
        super().__init__("Utseende (gäller hela appen)", parent)
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


class SettingsDialog(QDialog):
    """Vyens inställningar; ändringar sparas direkt och Stäng lämnar dem orörda."""

    def __init__(self, title: str, sections: list[QWidget], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        for section in sections:
            layout.addWidget(section)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("Stäng")
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


def settings_button(parent: QWidget, title: str, sections) -> QPushButton:
    """Knapp som öppnar vyens inställningar (Alt+I, TASK-41)."""
    button = QPushButton(mnemonic("Inställningar", "I"), parent)
    button.clicked.connect(
        lambda: SettingsDialog(title, sections(), parent.window()).exec()
    )
    return button
