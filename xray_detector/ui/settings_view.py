from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from xray_detector.ui.theme import THEMES, apply_theme, current_theme


class SettingsView(QWidget):
    def __init__(self, settings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        layout = QVBoxLayout(self)
        layout.addStretch(0)
        layout.addWidget(self._build_theme_box())
        layout.addWidget(self._build_schedule_box())
        layout.addStretch(1)

    def _build_theme_box(self) -> QGroupBox:
        box = QGroupBox("Utseende")
        form = QFormLayout(box)
        self.theme_label = QLabel("Tema:")
        self.theme_combo = QComboBox()
        for key, label in THEMES.items():
            self.theme_combo.addItem(label, key)
        index = self.theme_combo.findData(current_theme())
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        form.addRow(self.theme_label, self.theme_combo)
        box.setLayout(form)
        return box

    def _build_schedule_box(self) -> QGroupBox:
        """Träningsschema: nattfönster och inaktivitetsgräns (TASK-7)."""
        box = QGroupBox("Träningsschema")
        form = QFormLayout(box)
        self.night_start = QSpinBox()
        self.night_start.setRange(0, 23)
        self.night_start.setValue(int(self.settings.value("training/night_start_hour", 23, type=int)))
        self.night_start.valueChanged.connect(
            lambda hour: self._save_clock(hour, is_start=True))
        form.addRow(QLabel("Nattfönster börjar (timme):"), self.night_start)
        self.night_end = QSpinBox()
        self.night_end.setRange(0, 23)
        self.night_end.setValue(int(self.settings.value("training/night_end_hour", 5, type=int)))
        self.night_end.valueChanged.connect(
            lambda hour: self._save_clock(hour, is_start=False))
        form.addRow(QLabel("Nattfönster slutar (timme):"), self.night_end)
        self.inactivity = QSpinBox()
        self.inactivity.setRange(1, 240)
        self.inactivity.setValue(int(self.settings.value("training/inactivity_minutes", 30, type=int)))
        self.inactivity.valueChanged.connect(
            lambda minutes: self.settings.setValue("training/inactivity_minutes", minutes))
        form.addRow(QLabel("Inaktivitet innan träning (min):"), self.inactivity)
        box.setLayout(form)
        return box

    def _save_clock(self, hour: int, is_start: bool) -> None:
        key = "training/night_start" if is_start else "training/night_end"
        self.settings.setValue(f"{key}_hour", hour)
        self.settings.setValue(key, f"{hour:02d}:00")

    def _on_theme_changed(self) -> None:
        from PySide6.QtWidgets import QApplication

        theme = self.theme_combo.currentData()
        self.settings.setValue("ui/theme", theme)
        apply_theme(QApplication.instance(), theme)
