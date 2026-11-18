"""Videopanel och resursmätare i detektionsvyn (TASK-31, TASK-145).

Panelerna låg tidigare i detection_view.py och flyttades hit när vyfilen
delades upp. StreamPanel äger en videoström: källväljare, upplösning, format,
bildruta, märken och återanslutning. ResourceMeter visar en resurs som etikett,
stapel och värde.
"""

from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from xray_detector.domain.capture import StreamFrame, VideoMode
from xray_detector.domain.detection import Detection
from xray_detector.infrastructure.video.devices import list_device_modes
from xray_detector.ui.badge import (
    BadgeTracker,
    badge_delays,
    badge_swap_frames,
    draw_badges,
)
from xray_detector.ui.colors import ERROR_COLOR, MUTED_TEXT, class_color
from xray_detector.ui.image_utils import bgr_to_qimage
from xray_detector.ui.shortcuts import mnemonic
from xray_detector.ui.style import button
from xray_detector.ui.video_file_dialog import remember_video_file, video_file_dir
from xray_detector.ui.video_settings import (
    clear_video_mode,
    load_video_mode,
    save_video_mode,
)

NO_SOURCE = "Ingen videokälla"
OPEN_FILE = "Öppna videofil..."
UVC_PREFIX = "UVC "
MAX_AUTO_RETRIES = 2
RETRY_TIMEOUT_MS = 1500
S_LOST = "Källa tappad"
S_CONNECTING = "Ansluter  (försök {0}/{1})"
S_LOST_AFTER = "Källan tappad efter {0} försök"
S_RETRY = "Försök igen"
S_PAUSED = "Avstängt under träning"
AUTO_MODE = "Auto"
# etiketten på rutan ritas i källans upplösning och skalas med bilden, så
# punktstorleken är dubbelt så stor som tidigare för att synas (TASK-84)
LABEL_POINT_SIZE = 20
LABEL_GAP = 4


def draw_detections(painter: QPainter, detections: list[Detection]) -> None:
    """Ritar ruta och etikett för varje detektion (TASK-76, TASK-84).

    Etiketten läggs ovanför rutan när det finns plats och strax innanför
    överkanten annars, så en detektion högt upp i bilden inte klipps.
    """
    pen = QPen()
    pen.setWidth(2)
    font = QFont()
    font.setPointSize(LABEL_POINT_SIZE)
    painter.setFont(font)
    metrics = painter.fontMetrics()
    for detection in detections:
        color = class_color(detection.class_name)
        pen.setColor(color)
        painter.setPen(pen)
        painter.drawRect(
            int(detection.x1),
            int(detection.y1),
            int(detection.width),
            int(detection.height),
        )
        baseline = int(detection.y1) - LABEL_GAP
        if baseline - metrics.ascent() < 0:
            baseline = int(detection.y1) + LABEL_GAP + metrics.ascent()
        painter.drawText(
            int(detection.x1),
            baseline,
            f"{detection.class_name} {detection.confidence * 100:.0f}%",
        )


class ResourceMeter(QWidget):
    """Etikett, stapel och värde för en resurs (TASK-31)."""

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.title = QLabel(title)
        self.title.setStyleSheet(f"color: {MUTED_TEXT};")
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
    source_requested = Signal(str, str, object, object)

    def __init__(
        self,
        source_id: str,
        devices=None,
        settings=None,
        retry_letter: str = "G",
        badge_align_right: bool = True,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.source_id = source_id
        self.devices = list(devices or [])
        self.settings = settings
        self.badge_align_right = badge_align_right
        show_frames, hide_frames = badge_delays(settings)
        self.badge = BadgeTracker(show_frames, hide_frames, badge_swap_frames(settings))
        self.latest: StreamFrame | None = None
        self._active: tuple[str, object] = ("none", None)
        self._lost_attempts = 0
        self._last_selected_index = 0
        self._modes: list[VideoMode] = []
        self.setMinimumSize(2, 2)
        self.setFrameShape(QFrame.Shape.Box)
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self.fps_label = QLabel()
        self.fps_label.setFont(QFont("", 12, QFont.Weight.Bold))
        self.source_combo = QComboBox()
        self.source_combo.addItem(NO_SOURCE, "none")
        for device in self.devices:
            label = f"{UVC_PREFIX}{device.index}"
            if device.name and not device.name.startswith("Video "):
                label = f"{label} · {device.name}"
            self.source_combo.addItem(label, f"uvc:{device.index}")
        self.source_combo.addItem(OPEN_FILE, "file")
        self.source_combo.currentIndexChanged.connect(self._on_source_changed)
        self.resolution_combo = QComboBox()
        self.resolution_combo.setToolTip("Upplösning som enheten erbjuder")
        self.resolution_combo.currentIndexChanged.connect(self._on_resolution_changed)
        self.format_combo = QComboBox()
        self.format_combo.setToolTip("Pixelformat; MJPG klarar högre bildfrekvens än YUY2")
        self.format_combo.currentIndexChanged.connect(self._on_format_changed)
        self._set_mode_controls_visible(False)
        top.addWidget(self.fps_label)
        top.addStretch(1)
        top.addWidget(self.source_combo)
        top.addWidget(self.resolution_combo)
        top.addWidget(self.format_combo)
        layout.addLayout(top)
        self.display = QLabel()
        self.display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.display, 1)
        self.lost_widget = QWidget()
        lost_layout = QVBoxLayout(self.lost_widget)
        lost_layout.addStretch(1)
        self.lost_label = QLabel(S_LOST)
        self.lost_label.setStyleSheet(
            f"color: {ERROR_COLOR}; font-size: 16px; font-weight: bold;"
        )
        self.lost_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.retry_button = button(mnemonic(S_RETRY, retry_letter))
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
        if not value:
            value = None
        elif kind == "uvc":
            value = int(value)
        if kind == "none":
            self._active = ("none", None)
            self._set_mode_controls_visible(False)
            self.source_requested.emit(self.source_id, "none", None, None)
            self._show_no_source()
        elif kind == "file" and value:
            # sparad/vald fil: starta direkt utan dialog (TASK-23)
            self._activate_file(value)
        elif kind == "file":
            pressed_index = self._last_selected_index
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Välj videofil",
                video_file_dir(self.settings),
                "Videofiler (*.mp4 *.avi *.mkv *.mov)",
            )
            if path:
                remember_video_file(self.settings, path)
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
            self._populate_modes(value)
            self.source_requested.emit(self.source_id, "uvc", value, self.current_mode())

        self._last_selected_index = self.source_combo.currentIndex()
        self.latest = None

    def _populate_modes(self, device_index: int) -> None:
        """Fyller upplösnings- och formatlistorna från enhetens kapabiliteter (TASK-39)."""
        self._modes = list_device_modes(device_index)
        saved = self._saved_mode()
        self.resolution_combo.blockSignals(True)
        self.resolution_combo.clear()
        self.resolution_combo.addItem(AUTO_MODE, "")
        for width, height in dict.fromkeys((m.width, m.height) for m in self._modes):
            self.resolution_combo.addItem(f"{width}x{height}", f"{width}x{height}")
        self.resolution_combo.blockSignals(False)
        if saved is not None:
            position = self.resolution_combo.findData(f"{saved.width}x{saved.height}")
            if position >= 0:
                self.resolution_combo.setCurrentIndex(position)
        self._populate_formats(saved.fourcc if saved else "")
        self._set_mode_controls_visible(True)

    def _populate_formats(self, preferred: str = "") -> None:
        """Formaten som den valda upplösningen erbjuder."""
        resolution = self.resolution_combo.currentData()
        formats = [
            mode.fourcc
            for mode in self._modes
            if not resolution or f"{mode.width}x{mode.height}" == resolution
        ]
        self.format_combo.blockSignals(True)
        self.format_combo.clear()
        for fourcc in dict.fromkeys(formats):
            self.format_combo.addItem(fourcc or "Auto", fourcc)
        self.format_combo.blockSignals(False)
        position = self.format_combo.findData(preferred)
        if position >= 0:
            self.format_combo.setCurrentIndex(position)
        self.format_combo.setEnabled(bool(resolution))

    def _set_mode_controls_visible(self, visible: bool) -> None:
        self.resolution_combo.setVisible(visible)
        self.format_combo.setVisible(visible)

    def current_mode(self) -> VideoMode | None:
        """Vald upplösning och format, eller None när drivrutinen får välja."""
        resolution = self.resolution_combo.currentData()
        if not resolution:
            return None
        width, _, height = resolution.partition("x")
        return VideoMode(int(width), int(height), self.format_combo.currentData() or "")

    def _saved_mode(self) -> VideoMode | None:
        if self.settings is None:
            return None
        return load_video_mode(self.settings, self.source_id)

    def _on_resolution_changed(self, *_args) -> None:
        self._populate_formats(self.format_combo.currentData() or "")
        self._on_mode_changed()

    def _on_format_changed(self, *_args) -> None:
        self._on_mode_changed()

    def _on_mode_changed(self) -> None:
        """Sparar valet och startar om strömmen med det nya formatet."""
        mode = self.current_mode()
        if self.settings is not None:
            if mode is None:
                clear_video_mode(self.settings, self.source_id)
            else:
                save_video_mode(self.settings, self.source_id, mode)
        kind, value = self._active
        if kind == "uvc":
            self.source_requested.emit(self.source_id, kind, value, mode)

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
        self._set_mode_controls_visible(False)
        self.source_requested.emit(self.source_id, "file", Path(path), None)

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

    def _show_message(self, text: str) -> None:
        """Visar en text i stället för bilden och släpper senaste ramen."""
        self.display.setText(text)
        # bakgrunden kommer ur paletten, så ljust tema inte får en svart ruta (TASK-144)
        self.display.setStyleSheet(f"color: {MUTED_TEXT}; font-size: 24px;")
        self.display.setAutoFillBackground(True)
        self.display.show()
        self.lost_widget.hide()
        self.fps_label.clear()
        self.latest = None

    def _show_no_source(self) -> None:
        self._show_message(NO_SOURCE)

    def show_paused(self) -> None:
        """Visar att strömmen är avstängd medan träningen körs (TASK-74)."""
        self._show_message(S_PAUSED)

    def restart_source(self) -> None:
        """Startar om strömmen med samma källa som senast (TASK-74)."""
        kind, value = self._active
        if kind == "none":
            return
        self.reset_connection_state()
        self.source_requested.emit(self.source_id, kind, value, self.current_mode())

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
        self.source_requested.emit(self.source_id, kind, value, self.current_mode())

    def reset_connection_state(self) -> None:
        self._lost_attempts = 0
        self.lost_widget.hide()
        self.display.show()

    def show_frame(self, stream_frame: StreamFrame) -> None:
        if self._lost_attempts:
            self.reset_connection_state()
        self.latest = stream_frame
        self.fps_label.setText(f"{stream_frame.fps:.1f} fps" if stream_frame.fps else "")
        image = self._to_qimage(stream_frame.frame)
        painter = QPainter(image)
        draw_detections(painter, stream_frame.detections)
        painter.end()
        scaled = QPixmap.fromImage(image).scaled(
            self.display.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._draw_badges(scaled, stream_frame.detections)
        self.display.setPixmap(scaled)

    def _draw_badges(self, pixmap: QPixmap, detections: list[Detection]) -> None:
        """Ritar klassmärkena på den skalade bilden (TASK-84).

        Ett märke per klass som syns i ramen, staplade uppifrån och ned. De
        ritas efter skalningen, så de har samma storlek oavsett källans
        upplösning och hamnar högst upp i själva videobilden.
        """
        badges = self.badge.update(detections)
        if not badges:
            return
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw_badges(painter, pixmap.rect(), badges, align_right=self.badge_align_right)
        painter.end()

    def set_badge_settings(
        self, show_frames: int, hide_frames: int, swap_frames: int
    ) -> None:
        """Nya fördröjningar och ny tröghet för klassmärket, utan att rita om bilden.

        Fördröjningarna styr när märket visas och döljs (TASK-84) och
        trögheten hur ofta märkena byter plats (TASK-86).
        """
        self.badge.set_delays(show_frames, hide_frames)
        self.badge.set_swap_frames(swap_frames)

    def clear_overlay(self) -> None:
        if self.latest is not None:
            self.latest.detections = []
            self.badge.reset()
            self.show_frame(self.latest)

    @staticmethod
    def _to_qimage(frame: np.ndarray) -> QImage:
        """BGR-ramen som QImage; kopian och konverteringen delas med vyerna (TASK-140)."""
        return bgr_to_qimage(frame)


