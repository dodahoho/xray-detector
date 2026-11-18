import json
import logging
import time

from PySide6.QtCore import QEvent, QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from xray_detector.application import model_registry
from xray_detector.application.background_task import BackgroundTask
from xray_detector.domain.capture import StreamFrame, VideoMode
from xray_detector.domain.config import AppConfig
from xray_detector.infrastructure.detectors.base import BaseDetector
from xray_detector.infrastructure.system.resources import ResourceMonitor, ResourceUsage
from xray_detector.infrastructure.video.camera_service import CameraService
from xray_detector.infrastructure.video.devices import list_devices
from xray_detector.infrastructure.video.source import build_source
from xray_detector.ui.badge import (
    badge_delays,
    badge_swap_frames,
)
from xray_detector.ui.busy_indicator import BusyIndicator
from xray_detector.ui.colors import (
    device_color,
)
from xray_detector.ui.model_combo import ModelComboBox
from xray_detector.ui.settings_dialog import (
    NO_CLASSES,
    BadgeSection,
    ClassFilterSection,
    settings_button,
)
from xray_detector.ui.shortcuts import bind_shortcut, mnemonic, with_hint
from xray_detector.ui.stream_panel import ResourceMeter, StreamPanel
from xray_detector.ui.style import button

DETECTION_TURN_OFF = mnemonic("Detektion av", "O")
DETECTION_TURN_ON = mnemonic("Detektion på", "O")
CLASSES_OFF_PREFIX = "detection/classes_off"


def _fraction(value: int | None, total: int | None) -> float | None:
    if value is None or not total:
        return None
    return value / total


def _format_bytes(value: int | None) -> str:
    if value is None:
        return ""
    size = float(value)
    for unit in ("B", "kB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return ""


def _format_pair(value: int | None, total: int | None) -> str:
    if value is None or total is None:
        return ""
    return f"{_format_bytes(value)} / {_format_bytes(total)}"


class _CaptureKeyFilter(QObject):
    """Låter Space fånga även när ett inmatningsfält i vyn har fokus (TASK-114).

    Ett textfält som QDoubleSpinBox accepterar ShortcutOverride för Space,
    eftersom tecknet kan skrivas in i fältet, och då hinner genvägen aldrig
    utlösas. Filtret avvisar överstyrningen innan fältet ser den, så Space
    alltid betyder fånga i den här vyn. Det sitter på vyens fält i stället för
    på applikationen, så bara deras händelser går genom Python.
    """

    def eventFilter(self, obj, event) -> bool:
        if event.type() != QEvent.Type.ShortcutOverride:
            return False
        if event.key() != Qt.Key.Key_Space:
            return False
        event.ignore()
        return True


class DetectionView(QWidget):
    capture_requested = Signal(object)
    error_occurred = Signal(str)

    def __init__(self, config: AppConfig, settings, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.settings = settings
        self.camera_service = CameraService()
        self.detector = None
        self.detection_enabled = True
        self._paused = False
        self._model_task: BackgroundTask | None = None
        self._device_task: BackgroundTask | None = None
        self._loading_spec = None
        self._model_started: float | None = None
        # modellnyckel -> modellens klassnamn, så klassfiltret kan listas även
        # när detektorn är pausad (TASK-53)
        self._model_classes: dict[str, list[str]] = {}
        layout = QVBoxLayout(self)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Modell:"))
        self.model_combo = ModelComboBox()
        self.refresh_models()
        self._select_model(config.default_model)
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)
        bar.addWidget(self.model_combo)
        bar.addWidget(QLabel("Tröskel:"))
        self.conf_spin = QDoubleSpinBox()
        self.conf_spin.setRange(0.05, 0.95)
        self.conf_spin.setSingleStep(0.05)
        self.conf_spin.setValue(config.confidence_threshold)
        self.conf_spin.valueChanged.connect(self._on_threshold_changed)
        bar.addWidget(self.conf_spin)
        self.device_label = QLabel("Enhet: kontrollerar...")
        self.device_label.setStyleSheet("font-weight: bold;")
        bar.addWidget(self.device_label)
        self.resource_monitor = ResourceMonitor()
        self.resource_meters = {
            "gpu": ResourceMeter("GPU"),
            "vram": ResourceMeter("VRAM"),
            "cpu": ResourceMeter("CPU"),
            "ram": ResourceMeter("RAM"),
        }
        for meter in self.resource_meters.values():
            bar.addWidget(meter)
        bar.addStretch(1)
        self.capture_button = button(
            with_hint(mnemonic("Fånga bilder", "F"), "Space"), primary=True
        )
        self.capture_button.clicked.connect(self._on_capture)
        bar.addWidget(self.capture_button)
        # Space fångar som knappen, men bara när detektionsvyn är den aktiva fliken
        bind_shortcut(self, "Space", self._on_capture)
        self.detection_button = button(DETECTION_TURN_OFF)
        self.detection_button.setCheckable(True)
        self.detection_button.setChecked(True)
        self.detection_button.setToolTip("Slår av och på objektdetektionen i båda strömmarna")
        self.detection_button.toggled.connect(self._on_detection_toggled)
        bar.addWidget(self.detection_button)
        self.settings_button = settings_button(
            self, "Inställningar – Detektion", self._settings_sections
        )
        bar.addWidget(self.settings_button)
        layout.addLayout(bar)
        panels = QHBoxLayout()
        devices = list_devices()
        logging.getLogger("xray").info(
            "Kameror: %s",
            ", ".join(f"{device.index}={device.name}" for device in devices)
            or "inga hittade",
        )
        # märkena sitter mot mitten, så de två fönstren visar klasserna nära varandra
        self.left = StreamPanel(
            "left", devices, self.settings, retry_letter="G", badge_align_right=True
        )
        self.right = StreamPanel(
            "right", devices, self.settings, retry_letter="N", badge_align_right=False
        )
        for panel in (self.left, self.right):
            panel.source_requested.connect(self._on_source_requested)
            panels.addWidget(panel, 1)
        layout.addLayout(panels, 1)
        self.resource_timer = QTimer(self)
        self.resource_timer.setInterval(1000)
        self.resource_timer.timeout.connect(self._update_resources)
        self.resource_timer.start()
        self._update_resources()
        self.busy = BusyIndicator(self)
        # Space fångar även när ett fält i vyn har fokus (TASK-114)
        self._capture_key_filter = _CaptureKeyFilter(self)
        for field in self.findChildren(QWidget):
            if field.focusPolicy() != Qt.FocusPolicy.NoFocus:
                field.installEventFilter(self._capture_key_filter)

    def _update_resources(self) -> None:
        """Uppdaterar resursstaplarna med ett nytt ögonblicksvärde (TASK-31)."""
        self._apply_usage(self.resource_monitor.sample())

    def _apply_usage(self, usage: ResourceUsage) -> None:
        # psutil räknar process-CPU per kärna (kan bli > 100 %): visa andel av maskinen
        cpu_share = None
        if usage.cpu_percent is not None and usage.cpu_count:
            cpu_share = usage.cpu_percent / (100.0 * usage.cpu_count)
        self.resource_meters["gpu"].set_usage(
            None if usage.gpu_percent is None else usage.gpu_percent / 100.0,
            "" if usage.gpu_percent is None else f"{usage.gpu_percent:.0f}%",
        )
        self.resource_meters["vram"].set_usage(
            _fraction(usage.vram_bytes, usage.vram_total_bytes),
            _format_pair(usage.vram_bytes, usage.vram_total_bytes),
        )
        self.resource_meters["cpu"].set_usage(
            cpu_share,
            "" if cpu_share is None else f"{cpu_share * 100:.0f}%",
        )
        self.resource_meters["ram"].set_usage(
            _fraction(usage.ram_bytes, usage.ram_total_bytes),
            _format_bytes(usage.ram_bytes),
        )

    def refresh_models(self) -> None:
        """Fyller modellväljaren med basmodeller plus egentränade modeller."""
        self.model_combo.fill(
            model_registry.available_models(
                self.config.models_dir, self.config.trained_dir
            ),
            self.model_combo.currentData(),
        )
        self._specs = self.model_combo.specs
        self._select_model(self.model_combo.currentData())

    def _select_model(self, key: str | None) -> bool:
        """Väljer modellen om den finns och är tillgänglig."""
        index = self.model_combo.findData(key) if key else -1
        if index < 0 or not self.model_combo.enabled(index):
            return False
        self.model_combo.setCurrentIndex(index)
        return True

    def restore_settings(self) -> None:
        model_key = self.settings.value("detection/model", type=str)
        if model_key:
            self._select_model(model_key)
        confidence = self.settings.value("detection/confidence", type=float)
        if confidence:
            self.conf_spin.setValue(confidence)
        for panel in (self.left, self.right):
            kind = self.settings.value(f"detection/source_{panel.source_id}_kind", type=str)
            value = self.settings.value(f"detection/source_{panel.source_id}_value")
            if kind:
                panel.restore_source(kind, value)

    def save_settings(self) -> None:
        self.settings.setValue("detection/model", self.model_combo.currentData())
        self.settings.setValue("detection/confidence", self.conf_spin.value())
        for panel in (self.left, self.right):
            kind, value = panel.current_source()
            self.settings.setValue(f"detection/source_{panel.source_id}_kind", kind)
            self.settings.setValue(f"detection/source_{panel.source_id}_value", value)

    def _settings_sections(self) -> list:
        """Detektionsvyns egna inställningar: klassfiltret och klassmärket.

        Klassfiltret följer vald modell (TASK-53) och märkets fördröjningar
        styr hur snabbt en klass visas och döljs i videofönstren (TASK-84).
        Trögheten i märkenas platsbyten ställs in på samma ställe (TASK-86).
        """
        return [
            ClassFilterSection(
                self.model_class_names(),
                self._disabled_classes(self.model_combo.currentData()),
                self._on_class_filter_changed,
            ),
            BadgeSection(self.settings, self._on_badge_delays_changed),
        ]

    def _on_badge_delays_changed(self) -> None:
        """Nya märkesinställningar slår igenom direkt på båda panelerna."""
        show_frames, hide_frames = badge_delays(self.settings)
        swap_frames = badge_swap_frames(self.settings)
        for panel in (self.left, self.right):
            panel.set_badge_settings(show_frames, hide_frames, swap_frames)

    def model_class_names(self) -> list[str]:
        """Klasserna som vald modell kan detektera (TASK-52, TASK-53, TASK-61)."""
        return list(self._model_classes.get(self.model_combo.currentData(), []))

    def _classes_key(self, model_key: str) -> str:
        return f"{CLASSES_OFF_PREFIX}/{model_key}"

    def _disabled_classes(self, model_key: str) -> set[str]:
        """Klasser användaren valt bort för modellen; tomt när inget sparats.

        Bortval sparas i stället för val, så en klass som tillkommer i en
        modell är vald från början (TASK-53).
        """
        raw = self.settings.value(self._classes_key(model_key), "", type=str)
        try:
            names = json.loads(raw) if raw else []
        except ValueError:
            return set()
        return {str(name) for name in names} if isinstance(names, list) else set()

    def _save_disabled_classes(self, model_key: str, names: set[str]) -> None:
        self.settings.setValue(self._classes_key(model_key), json.dumps(sorted(names)))

    def _enabled_classes(self) -> list[str]:
        """Modellens klasser som användaren har valt kvar (TASK-53)."""
        if self.detector is None:
            return []
        disabled = self._disabled_classes(self.model_combo.currentData())
        return [name for name in self.detector.class_names if name not in disabled]

    def _on_class_filter_changed(self, selected: list[str]) -> None:
        """Sparar valet för modellen och filtrerar detektionerna direkt (TASK-53)."""
        names = self.model_class_names()
        self._save_disabled_classes(
            self.model_combo.currentData(),
            {name for name in names if name not in selected},
        )
        self._apply_class_filter()

    def _apply_class_filter(self) -> None:
        """Ger detektorn de valda klasserna, eller kopplar bort den när inga är valda."""
        if self.detector is None:
            return
        enabled = self._enabled_classes()
        self.detector.set_enabled_classes(enabled)
        if not enabled:
            self.error_occurred.emit(NO_CLASSES)
            self.camera_service.set_detector(None)
            for panel in (self.left, self.right):
                panel.clear_overlay()
            return
        if not self._paused:
            self.camera_service.set_detector(self._active_detector())

    def _on_source_requested(
        self, source_id: str, kind: str, value: object, mode: VideoMode | None = None
    ) -> None:
        worker = self.camera_service.set_source(
            source_id, build_source(kind, value, mode)
        )
        if worker is not None:
            worker.frame_ready.connect(self._on_frame)
            worker.source_lost.connect(self._on_source_lost)
            worker.error_occurred.connect(self._on_error)
            worker.set_detector(self._active_detector())

    def _on_frame(self, stream_frame: StreamFrame) -> None:
        panel = self.left if stream_frame.source_id == "left" else self.right
        panel.show_frame(stream_frame)

    def _on_source_lost(self, source_id: str) -> None:
        panel = self.left if source_id == "left" else self.right
        panel.show_source_lost()

    def _on_error(self, source_id: str, message: str) -> None:
        self.error_occurred.emit(f"Detektorfel ({source_id}): {message}")

    def _on_threshold_changed(self) -> None:
        """Tröskeln ändras utan att modellen laddas om (TASK-36)."""
        if self.detector is not None:
            self.detector.set_confidence_threshold(self.conf_spin.value())

    def _active_detector(self) -> BaseDetector | None:
        """Detektorn som ska köra nu; ingen när detektionen eller alla klasser är av.

        Avstängd detektion (TASK-38) och ett klassfilter utan valda klasser
        (TASK-53) betyder samma sak för strömmarna: ingen detektor alls.
        """
        if not self.detection_enabled or not self._enabled_classes():
            return None
        return self.detector

    def _on_detection_toggled(self, enabled: bool) -> None:
        """Slår av/på detektionen utan att modellen laddas om (TASK-38)."""
        self.detection_enabled = enabled
        # knapptexten säger vad ett klick gör, inte vad läget är
        self.detection_button.setText(
            DETECTION_TURN_OFF if enabled else DETECTION_TURN_ON
        )
        if not enabled:
            self.camera_service.set_detector(None)
            for panel in (self.left, self.right):
                panel.clear_overlay()
        elif self.detector is None:
            self._on_model_changed()
        else:
            self.camera_service.set_detector(self._active_detector())

    def _on_model_changed(self) -> None:
        """Laddar modellen i en arbetstråd så indikatorn kan animeras (TASK-40)."""
        if self._model_task is not None:
            return
        spec = self._specs.get(self.model_combo.currentData())
        if spec is None:
            self.error_occurred.emit("Kunde inte ladda modell: okänt modellval")
            return
        threshold = self.conf_spin.value()
        self.error_occurred.emit("Laddar modell...")
        self.model_combo.setEnabled(False)
        self.busy.start(f"Laddar {spec.label}...")
        self._loading_spec = spec
        self._model_started = time.monotonic()
        logging.getLogger("xray").info(
            "Laddar modell: %s (familj %s) från %s", spec.label, spec.family, spec.weights
        )
        task = BackgroundTask(lambda: self._create_detector(spec, threshold))
        task.succeeded.connect(self._on_model_loaded)
        task.failed.connect(self._on_model_failed)
        task.finished.connect(self._on_model_task_finished)
        self._model_task = task
        task.start()

    def _create_detector(self, spec, threshold: float) -> BaseDetector:
        """Skapar detektorn i arbetstråden; modulen slås upp där så den går att byta ut."""
        return model_registry.create_detector(spec, threshold)

    def _on_model_loaded(self, detector: BaseDetector) -> None:
        self.detector = detector
        self._model_classes[self._loading_spec.key] = list(detector.class_names)
        self._apply_class_filter()
        device_label = getattr(detector, "device_label", "")
        if device_label:
            self.device_label.setText(f"Enhet: {device_label}")
        elapsed = 0.0 if self._model_started is None else time.monotonic() - self._model_started
        logging.getLogger("xray").info(
            "Modell laddad: %s familj=%s vikter=%s enhet=%s på %.1f s",
            self._loading_spec.label,
            self._loading_spec.family,
            self._loading_spec.weights,
            device_label or "okänd",
            elapsed,
        )
        self.error_occurred.emit(f"Modell laddad: {self._loading_spec.label}")

    def _on_model_failed(self, message: str) -> None:
        self.detector = None
        self.camera_service.set_detector(None)
        self.error_occurred.emit(f"Kunde inte ladda modell: {message}")

    def _on_model_task_finished(self) -> None:
        self._model_task = None
        self.busy.stop()
        self.model_combo.setEnabled(True)

    def check_device(self) -> None:
        """Kontrollerar enheten i en arbetstråd: CUDA-initieringen tar cirka 1 s (TASK-40)."""
        self.device_label.setText("Enhet: kontrollerar...")
        task = BackgroundTask(model_registry.device_status)
        task.succeeded.connect(self._apply_device_status)
        self._device_task = task
        task.start()

    def _apply_device_status(self, text: str) -> None:
        self.device_label.setText(text)
        self.device_label.setStyleSheet(
            f"font-weight: bold; color: {device_color(text)};"
        )

    def wait_for_background(self, timeout_ms: int = 10000) -> None:
        """Väntar in modelladdning och enhetskontroll (tester och stängning)."""
        for task in (self._model_task, self._device_task):
            if task is not None:
                task.wait(timeout_ms)

    def _on_capture(self) -> None:
        captures: list[StreamFrame] = [
            panel.latest for panel in (self.left, self.right) if panel.latest is not None
        ]
        if not captures:
            self.error_occurred.emit("Ingen videokälla att fånga ifrån")
            return
        self.capture_requested.emit(captures)

    def pause_detection(self) -> None:
        """Stänger av strömmarna och detektionen och släpper detektorns GPU-minne.

        Träningen får hela maskinen: både videofångsten (UVC), uppspelningen av
        videofil och detektionen i strömmen stängs av (TASK-6, TASK-74).
        """
        self._paused = True
        self.camera_service.set_detector(None)
        self.camera_service.stop_all()
        self.detector = None
        for panel in (self.left, self.right):
            panel.clear_overlay()
            panel.show_paused()
        try:
            # torch är tungt och valfritt, så det importeras först vid tömningen
            import torch  # noqa: PLC0415

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

    def resume_streams(self) -> None:
        """Startar strömmarna och detektionen igen efter träningspausen (TASK-74).

        Anropas när träningen avslutas och när användaren går till fliken
        Detektion, så strömmarna tänds igen utan att träningen behöver vara klar.
        """
        if not self._paused:
            return
        self._paused = False
        for panel in (self.left, self.right):
            panel.restart_source()
        if not self.detection_enabled:
            # anvandaren har slagit av detektionen: lat den vara av efter traningen
            return
        if self.detector is None:
            # detektorn slappes vid paus for VRAM-frigoring: abygg fran modellvalet
            self._on_model_changed()
        else:
            self.camera_service.set_detector(self._active_detector())

    def resume_detection(self) -> None:
        """Återupptar strömmarna och detektionen när träningen är klar (TASK-6)."""
        self.resume_streams()

    def stop(self) -> None:
        self.camera_service.stop_all()
        self.wait_for_background()
