"""Applikationens globala inställningar (TASK-43).

Fliken håller sådant som inte hör till någon av de andra flikarna. Vyernas egna
inställningar ligger i respektive vys inställningsknapp (settings_dialog.py).
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget

from xray_detector.domain.config import AppConfig
from xray_detector.ui.model_settings import ModelSection
from xray_detector.ui.settings_dialog import ThemeSection


class SettingsView(QWidget):
    """Globala inställningar: sådant som inte hör till någon av de andra flikarna."""

    models_changed = Signal()

    def __init__(self, config: AppConfig, settings, parent=None, active_run_dir=None) -> None:
        super().__init__(parent)
        self.config = config
        self.settings = settings
        self.theme_section = ThemeSection(settings)
        # en pågående träning får inte raderas från modellistan (TASK-129)
        self.model_section = ModelSection(
            config.models_dir, config.trained_dir, active_run_dir=active_run_dir
        )
        # väljarna i detektions- och träningsvyn bygger om sina listor (TASK-81)
        self.model_section.models_changed.connect(self.models_changed)
        layout = QVBoxLayout(self)
        layout.addStretch(0)
        # korten håller sig till vänster, så fälten inte växer över skärmen (TASK-82)
        layout.addWidget(self.theme_section, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.model_section, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)
