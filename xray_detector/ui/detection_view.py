from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from xray_detector.application.video_service import VideoService
from xray_detector.domain.capture import StreamFrame
from xray_detector.domain.config import AppConfig
from xray_detector.infrastructure.detectors.base import BaseDetector
from xray_detector.infrastructure.system.resources import ResourceMonitor, ResourceUsage
from xray_detector.ui.video_settings import load_video_mode

NO_SOURCE = "Ingen videokälla"
OPEN_FILE = "Öppna videofil..."
UVC_PREFIX = "UVC "
MAX_AUTO_RETRIES = 2
RETRY_TIMEOUT_MS = 1500
S_LOST = "Källa tappad"
S_CONNECTING = "Ansluter  (försök {0}/{1})"
S_LOST_AFTER = "Källan tappad efter {0} försök"
S_RETRY = "Försök igen"
DETECTION_TURN_OFF = "Detektion av"
DETECTION_TURN_ON = "Detektion på"

from xray_detector.ui.colors import class_color


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


class ResourceMeter(QWidget):
    """Etikett, stapel och värde för en resurs (TASK-31)."""

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.title = QLabel(title)
        self.title.setStyleSheet("color: #888;")
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        self.bar.setFixedSize(56, 10)
        self.value = QLabel("-")
        self.value.setMinimumWidth(96)
        layout.addWidget(self.title)
        layout.addWidget(self.bar)
        layout.addWidget(self.value)

    def set_usage(self, fraction: float | None, text: str) -> None:
        if fraction is None:
            self.bar.setValue(0)
            self.value.setText("n/a")
            return
        self.bar.setValue(int(max(0.0, min(1.0, fraction)) * 100))
        self.value.setText(text)


class StreamPanel(QFrame):
    source_requested = Signal(str, str, object)

    def __init__(self, source_id: str, title: str, devices=None, parent=None) -> None:
        super().__init__(parent)
        self.source_id = source_id
        self.devices = list(devices or [])
        self.known_classes: list[str] = []
        self.latest: StreamFrame | None = None
        self._active: tuple[str, object] = ("none", None)
        self._base_title = title
        self._lost_attempts = 0
        self._last_selected_index = 0
        self.setMinimumSize(2, 2)
        self.setFrameShape(QFrame.Shape.Box)
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("", 12, QFont.Weight.Bold))
        self.source_combo = QComboBox()
        self.source_combo.addItem(NO_SOURCE, "none")
        for device in self.devices:
            label = f"{UVC_PREFIX}{device.index}"
            if device.name and not device.name.startswith("Video "):
                label = f"{label} · {device.name}"
            self.source_combo.addItem(label, f"uvc:{device.index}")
        self.source_combo.addItem(OPEN_FILE, "file")
        self.source_combo.currentIndexChanged.connect(self._on_source_changed)
        top.addWidget(self.title_label)
        top.addStretch(1)
        top.addWidget(self.source_combo)
        layout.addLayout(top)
        self.display = QLabel()
        self.display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.display, 1)
        self.lost_widget = QWidget()
        lost_layout = QVBoxLayout(self.lost_widget)
        lost_layout.addStretch(1)
        self.lost_label = QLabel(S_LOST)
        self.lost_label.setStyleSheet("color: #c33; font-size: 16px; font-weight: bold;")
        self.lost_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.retry_button = QPushButton(S_RETRY)
        self.retry_button.setMinimumHeight(36)
        self.retry_button.clicked.connect(self._on_retry)
        lost_layout.addWidget(self.lost_label)
        lost_layout.addWidget(self.retry_button, 0, Qt.AlignmentFlag.AlignHCenter)
        lost_layout.addStretch(1)
        self.lost_widget.hide()
        layout.addWidget(self.lost_widget, 1)
        self._show_no_source()

    def _on_source_changed(self, *_args) -> None:
        data = self.source_combo.currentData() or "none"
        kind, _, value = data.partition(":")
        if value:
            value = int(value) if kind == "uvc" else value
        else:
            value = None
        if kind == "none":
            self._active = ("none", None)
            self.source_requested.emit(self.source_id, "none", None)
            self._show_no_source()
        elif kind == "file" and value:
            # sparad/vald fil: starta direkt utan dialog (TASK-23)
            self._activate_file(value)
        elif kind == "file":
            pressed_index = self._last_selected_index
            path, _ = QFileDialog.getOpenFileName(
                self, "Välj videofil", "", "Videofiler (*.mp4 *.avi *.mkv *.mov)"
            )
            if path:
                self._activate_file(path)
            else:
                # avbruten dialog: aterhall det tidigare valet utan att emitetra
                self.source_combo.blockSignals(True)
                self.source_combo.setCurrentIndex(pressed_index)
                self.source_combo.blockSignals(False)
            self._last_selected_index = self.source_combo.currentIndex()
            self.latest = None
            return
        elif kind == "uvc":
            self._active = ("uvc", value)
            self.source_requested.emit(self.source_id, "uvc", value)

        self._last_selected_index = self.source_combo.currentIndex()
        self.latest = None

    def _activate_file(self, path) -> None:
        """Aktiverar en videofilskalla utan dialog och staller in komboposten."""
        item_data = f"file:{path}"
        self.source_combo.blockSignals(True)
        for index in reversed(range(self.source_combo.count())):
            data = str(self.source_combo.itemData(index) or "")
            if data.startswith("file:") and data != item_data:
                self.source_combo.removeItem(index)
        index = self.source_combo.findData(item_data)
        if index < 0:
            name = Path(path).name
            open_index = self.source_combo.findData("file")
            self.source_combo.insertItem(open_index, f"Videofil: {name}", item_data)
            index = self.source_combo.findData(item_data)
        self.source_combo.setCurrentIndex(index)
        self.source_combo.blockSignals(False)
        self._last_selected_index = index
        self._active = ("file", path)
        self.source_requested.emit(self.source_id, "file", Path(path))

    def current_source(self) -> tuple[str, object]:
        return self._active

    def restore_source(self, kind: str, value) -> None:
        if kind == "uvc" and value is not None:
            index = self.source_combo.findData(f"uvc:{int(value)}")
            if index >= 0:
                self.source_combo.setCurrentIndex(index)
        elif kind == "file" and value:
            self._activate_file(value)
        else:
            self.source_combo.setCurrentIndex(0)

    def _show_no_source(self) -> None:
        self.display.setText(NO_SOURCE)
        self.display.setStyleSheet("color: #888; font-size: 24px; background: #222;")
        self.display.show()
        self.lost_widget.hide()
        self.title_label.setText(self._base_title)
        self.latest = None

    def show_source_lost(self) -> None:
        """Kallan tappad: rakna upp, automatiska forsok och sedan knapp (TASK-19)."""
        self._lost_attempts += 1
        self.display.hide()
        self.lost_widget.show()
        if self._lost_attempts <= MAX_AUTO_RETRIES:
            self.lost_label.setText(S_CONNECTING.format(self._lost_attempts, MAX_AUTO_RETRIES + 1))
            self.retry_button.hide()
            QTimer.singleShot(RETRY_TIMEOUT_MS, self._on_retry)
        else:
            self.lost_label.setText(S_LOST_AFTER.format(self._lost_attempts))
            self.retry_button.show()

    def _on_retry(self) -> None:
        """Aterstartar senaste kallval utan att oppna menyn."""
        kind, value = self._active
        if kind == "none":
            self.display.hide()
            self.lost_widget.show()
            self.lost_label.setText(S_LOST)
            self.retry_button.show()
            return
        self.retry_button.hide()
        self.source_requested.emit(self.source_id, kind, value)

    def reset_connection_state(self) -> None:
        self._lost_attempts = 0
        self.lost_widget.hide()
        self.display.show()

    def show_frame(self, stream_frame: StreamFrame) -> None:
        if self._lost_attempts:
            self.reset_connection_state()
        self.latest = stream_frame
        parts = [self._base_title]
        if self._active[0] == "file" and stream_frame.source_label:
            parts.append(stream_frame.source_label)
        if stream_frame.fps:
            parts.append(f"{stream_frame.fps:.1f} fps")
        self.title_label.setText(" · ".join(parts))
        image = self._to_qimage(stream_frame.frame)
        painter = QPainter(image)
        pen = QPen()
        pen.setWidth(2)
        font = QFont()
        font.setPointSize(10)
        for detection in stream_frame.detections:
            color = class_color(detection.class_name, self.known_classes)
            pen.setColor(color)
            painter.setPen(pen)
            painter.drawRect(
                int(detection.x1),
                int(detection.y1),
                int(detection.width),
                int(detection.height),
            )
            painter.setFont(font)
            painter.drawText(
                int(detection.x1),
                max(12, int(detection.y1) - 4),
                f"{detection.class_name} {detection.confidence * 100:.0f}%",
            )
        painter.end()
        scaled = QPixmap.fromImage(image).scaled(
            self.display.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.display.setPixmap(scaled)


    def clear_overlay(self) -> None:
        if self.latest is not None:
            self.latest.detections = []
            self.show_frame(self.latest)

    @staticmethod
    def _to_qimage(frame: np.ndarray) -> QImage:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channels = rgb.shape
        return QImage(
            rgb.data, width, height, channels * width, QImage.Format.Format_RGB888
        )


class DetectionView(QWidget):
    capture_requested = Signal(object)
    error_occurred = Signal(str)

    def __init__(self, config: AppConfig, settings, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.settings = settings
        self.video_service = VideoService()
        self.detector = None
        self.detection_enabled = True
        layout = QVBoxLayout(self)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Modell:"))
        self.model_combo = QComboBox()
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
        self.capture_button = QPushButton("Fånga bilder")
        self.capture_button.setMinimumHeight(40)
        self.capture_button.clicked.connect(self._on_capture)
        bar.addWidget(self.capture_button)
        self.detection_button = QPushButton(DETECTION_TURN_OFF)
        self.detection_button.setCheckable(True)
        self.detection_button.setChecked(True)
        self.detection_button.setMinimumHeight(40)
        self.detection_button.setToolTip("Slår av och på objektdetektionen i båda strömmarna")
        self.detection_button.toggled.connect(self._on_detection_toggled)
        bar.addWidget(self.detection_button)
        layout.addLayout(bar)
        panels = QHBoxLayout()
        self.devices = self.video_service.list_devices()
        self.left = StreamPanel("left", "Ström 1", self.devices)
        self.right = StreamPanel("right", "ström 2", self.devices)
        for panel in (self.left, self.right):
            panel.known_classes = list(config.classes)
        for panel in (self.left, self.right):
            panel.source_requested.connect(self._on_source_requested)
            panels.addWidget(panel, 1)
        layout.addLayout(panels, 1)
        self.resource_timer = QTimer(self)
        self.resource_timer.setInterval(1000)
        self.resource_timer.timeout.connect(self._update_resources)
        self.resource_timer.start()
        self._update_resources()

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
        """Fyller modellväljaren med statiska specar plus nytränade modeller."""
        from xray_detector.application.model_registry import MODEL_SPECS, trained_models

        current = self.model_combo.currentData()
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self._specs = {}
        for spec in MODEL_SPECS:
            self.model_combo.addItem(spec.label, spec.key)
            self._specs[spec.key] = spec
        for spec in trained_models(self.config.models_dir):
            self.model_combo.addItem(spec.label, spec.key)
            self._specs[spec.key] = spec
        self._disable_unavailable_models()
        self._select_model(current)
        self.model_combo.blockSignals(False)

    def _disable_unavailable_models(self) -> None:
        """Avstänger modeller vars paket saknas (samma mönster som träningsvyn)."""
        import importlib.util

        missing = {"rfdetr": importlib.util.find_spec("rfdetr") is None}
        model = self.model_combo.model()
        for row in range(model.rowCount()):
            spec = self._specs.get(self.model_combo.itemData(row))
            if spec is None or not missing.get(spec.family, False):
                continue
            item = model.item(row)
            item.setEnabled(False)
            self.model_combo.setItemText(row, f"{item.text()} (rfdetr ej installerat)")

    def _select_model(self, key: str | None) -> bool:
        """Väljer modellen om den finns och är tillgänglig."""
        index = self.model_combo.findData(key) if key else -1
        if index < 0 or not self._model_enabled(index):
            return False
        self.model_combo.setCurrentIndex(index)
        return True

    def _model_enabled(self, index: int) -> bool:
        item = self.model_combo.model().item(index)
        return item is None or item.isEnabled()

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

    def _on_source_requested(self, source_id: str, kind: str, value: object) -> None:
        worker = self.video_service.set_source(
            source_id, kind, value, load_video_mode(self.settings)
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
        """Detektorn som ska köra nu; ingen alls när detektionen är avstängd (TASK-38)."""
        return self.detector if self.detection_enabled else None

    def _on_detection_toggled(self, enabled: bool) -> None:
        """Slår av/på detektionen utan att modellen laddas om (TASK-38)."""
        self.detection_enabled = enabled
        # knapptexten säger vad ett klick gör, inte vad läget är
        self.detection_button.setText(
            DETECTION_TURN_OFF if enabled else DETECTION_TURN_ON
        )
        if not enabled:
            self.video_service.set_detector(None)
            for panel in (self.left, self.right):
                panel.clear_overlay()
        elif self.detector is None:
            self._on_model_changed()
        else:
            self.video_service.set_detector(self.detector)

    def _on_model_changed(self) -> None:
        from xray_detector.application.model_registry import create_detector

        self.error_occurred.emit("Laddar modell...")
        try:
            spec = self._specs[self.model_combo.currentData()]
            self.detector = create_detector(
                spec, self.config.classes, self.conf_spin.value()
            )
            self.video_service.set_detector(self._active_detector())
            device_label = getattr(self.detector, "device_label", "")
            if device_label:
                self.device_label.setText(f"Enhet: {device_label}")
            self.error_occurred.emit(f"Modell laddad: {spec.label}")
        except Exception as exc:
            self.detector = None
            self.video_service.set_detector(None)
            self.error_occurred.emit(f"Kunde inte ladda modell: {exc}")

    def check_device(self) -> None:
        from xray_detector.application.model_registry import device_status

        text, color = device_status()
        self.device_label.setText(text)
        self.device_label.setStyleSheet(f"font-weight: bold; color: {color};")

    def _on_capture(self) -> None:
        captures: list[StreamFrame] = []
        for panel in (self.left, self.right):
            if panel.latest is not None:
                captures.append(panel.latest)
        if not captures:
            self.error_occurred.emit("Ingen videokälla att fånga ifrån")
            return
        self.capture_requested.emit(captures)

    def pause_detection(self) -> None:
        """Pausar detekteringen och slapper detektorns GPU-minne (TASK-6)."""
        self.video_service.set_detector(None)
        self.detector = None
        for panel in (self.left, self.right):
            panel.clear_overlay()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

    def resume_detection(self) -> None:
        if not self.detection_enabled:
            # anvandaren har slagit av detektionen: lat den vara av efter traningen
            return
        if self.detector is None:
            # detektorn slappes vid paus for VRAM-frigoring: abygg fran modellvalet
            self._on_model_changed()
        else:
            self.video_service.set_detector(self.detector)

    def stop(self) -> None:
        self.video_service.stop_all()
