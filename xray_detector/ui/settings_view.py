"""Applikationens globala inställningar (TASK-43).

Fliken håller sådant som inte hör till någon av de andra flikarna. Vyernas egna
inställningar ligger i respektive vys inställningsknapp (settings_dialog.py).
"""

from PySide6.QtWidgets import QVBoxLayout, QWidget

from xray_detector.ui.settings_dialog import ThemeSection


class SettingsView(QWidget):
    """Globala inställningar: sådant som inte hör till någon av de andra flikarna."""

    def __init__(self, settings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.theme_section = ThemeSection(settings)
        layout = QVBoxLayout(self)
        layout.addStretch(0)
        layout.addWidget(self.theme_section)
        layout.addStretch(1)
