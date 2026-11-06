from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
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
        layout.addWidget(box)
        layout.addStretch(1)

    def _on_theme_changed(self) -> None:
        from PySide6.QtWidgets import QApplication

        theme = self.theme_combo.currentData()
        self.settings.setValue("ui/theme", theme)
        apply_theme(QApplication.instance(), theme)
