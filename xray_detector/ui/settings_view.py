from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from xray_detector.domain.capture import VideoMode
from xray_detector.infrastructure.video.devices import list_device_modes
from xray_detector.ui.theme import THEMES, apply_theme, current_theme
from xray_detector.ui.video_settings import (
    clear_video_mode,
    load_video_mode,
    save_video_mode,
)

AUTO_MODE = "Auto (drivrutinen väljer)"


class SettingsView(QWidget):
    def __init__(self, settings, devices=None, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.devices = list(devices or [])
        self._modes: list[VideoMode] = []
        self._modes_loaded = False
        layout = QVBoxLayout(self)
        layout.addStretch(0)
        layout.addWidget(self._build_theme_box())
        layout.addWidget(self._build_video_box())
        layout.addWidget(self._build_schedule_box())
        layout.addStretch(1)

    def showEvent(self, event) -> None:
        """Läser enhetens kapabiliteter först när fliken öppnas (TASK-39).

        DirectShow-enumereringen instansierar enhetsfiltren, och för en
        virtuell kamera som NVIDIA Broadcast skriver drivrutinen då en rad
        loggrader. Det ska inte ske vid appstart.
        """
        super().showEvent(event)
        if not self._modes_loaded:
            self._modes_loaded = True
            self._reload_video_modes()

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

    def _build_video_box(self) -> QGroupBox:
        """UVC-källans upplösning och pixelformat (TASK-39).

        Listorna fylls från enhetens egna DirectShow-kapabiliteter, så det
        går att prova de lägen kortet faktiskt erbjuder. Valet sparas och
        används nästa gång en UVC-källa öppnas.
        """
        box = QGroupBox("Videokälla")
        form = QFormLayout(box)
        self.video_device = QComboBox()
        for device in self.devices:
            self.video_device.addItem(f"UVC {device.index} · {device.name}", device.index)
        self.video_device.currentIndexChanged.connect(self._reload_video_modes)
        form.addRow(QLabel("Enhet:"), self.video_device)
        self.video_resolution = QComboBox()
        self.video_resolution.currentIndexChanged.connect(self._on_resolution_changed)
        form.addRow(QLabel("Upplösning:"), self.video_resolution)
        self.video_format = QComboBox()
        self.video_format.currentIndexChanged.connect(self._save_video_mode)
        form.addRow(QLabel("Format:"), self.video_format)
        self.video_hint = QLabel("")
        self.video_hint.setStyleSheet("color: #888;")
        form.addRow(self.video_hint)
        box.setLayout(form)
        return box

    def _reload_video_modes(self, *_args) -> None:
        """Fyller upplösningslistan från den valda enhetens kapabiliteter."""
        index = self.video_device.currentData()
        self._modes = list_device_modes(index) if index is not None else []
        saved = load_video_mode(self.settings)
        self.video_resolution.blockSignals(True)
        self.video_resolution.clear()
        self.video_resolution.addItem(AUTO_MODE, "")
        for width, height in dict.fromkeys((m.width, m.height) for m in self._modes):
            self.video_resolution.addItem(f"{width}x{height}", f"{width}x{height}")
        self.video_resolution.blockSignals(False)
        if saved is not None:
            position = self.video_resolution.findData(f"{saved.width}x{saved.height}")
            if position >= 0:
                self.video_resolution.setCurrentIndex(position)
        self._reload_video_formats(saved.fourcc if saved else "")

    def _reload_video_formats(self, preferred: str = "") -> None:
        """Formaten som den valda upplösningen erbjuder."""
        resolution = self.video_resolution.currentData()
        formats = [
            mode.fourcc
            for mode in self._modes
            if not resolution or f"{mode.width}x{mode.height}" == resolution
        ]
        self.video_format.blockSignals(True)
        self.video_format.clear()
        for fourcc in dict.fromkeys(formats):
            self.video_format.addItem(fourcc or "Auto", fourcc)
        self.video_format.blockSignals(False)
        position = self.video_format.findData(preferred)
        if position >= 0:
            self.video_format.setCurrentIndex(position)
        self.video_format.setEnabled(bool(resolution))
        self._update_video_hint()

    def _on_resolution_changed(self, *_args) -> None:
        self._reload_video_formats(self.video_format.currentData() or "")
        self._save_video_mode()

    def _save_video_mode(self, *_args) -> None:
        resolution = self.video_resolution.currentData()
        if not resolution:
            clear_video_mode(self.settings)
        else:
            width, _, height = resolution.partition("x")
            save_video_mode(
                self.settings,
                VideoMode(
                    int(width),
                    int(height),
                    self.video_format.currentData() or "",
                ),
            )
        self._update_video_hint()

    def _update_video_hint(self) -> None:
        mode = load_video_mode(self.settings)
        self.video_hint.setText(
            "Drivrutinen väljer format"
            if mode is None
            else f"Används när en UVC-källa öppnas: {mode.label}"
        )

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
