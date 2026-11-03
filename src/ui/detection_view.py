from __future__ import annotations

from typing import Dict, List, Optional
import cv2
import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.core.models_schema import BoundingBox, CapturedFramePair, StreamFrameResult
from src.ui.annotation_canvas import color_for_class


class VideoStreamPanel(QWidget):
    """Visar en enskild videoström med inritade detektionsrektanglar, klassnamn och sannolikhet."""

    def __init__(self, stream_id: int, title: str, parent=None) -> None:
        super().__init__(parent)
        self.stream_id = stream_id
        self.title = title

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        header_layout = QHBoxLayout()
        self.title_label = QLabel(f"Ström {stream_id}: {title}")
        self.title_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #e2e8f0;")
        self.stats_label = QLabel("FPS: -- | Objekt: 0")
        self.stats_label.setStyleSheet("font-size: 13px; color: #94a3b8;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.stats_label)

        self.video_label = QLabel("Väntar på videoström...")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(420, 280)
        self.video_label.setStyleSheet(
            "background-color: #0f141b; border: 2px solid #263244; border-radius: 8px; color: #64748b; font-size: 15px;"
        )

        layout.addLayout(header_layout)
        layout.addWidget(self.video_label, stretch=1)

    def update_stream(self, result: StreamFrameResult) -> None:
        self.stats_label.setText(f"FPS: {result.fps:.1f} | Identifierade objekt: {len(result.detections)}")

        annotated = self._draw_detections(result.frame_bgr, result.detections)
        rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        qimg = QImage(rgb.data, w, h, rgb.strides[0], QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        scaled = pixmap.scaled(
            self.video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.video_label.setPixmap(scaled)

    @staticmethod
    def _draw_detections(frame_bgr: np.ndarray, detections: List[BoundingBox]) -> np.ndarray:
        canvas = frame_bgr.copy()
        for det in detections:
            qcol = color_for_class(det.class_name)
            bgr_color = (qcol.blue(), qcol.green(), qcol.red())

            x1, y1, x2, y2 = int(det.x1), int(det.y1), int(det.x2), int(det.y2)
            cv2.rectangle(canvas, (x1, y1), (x2, y2), bgr_color, 3)

            label = f"{det.class_name} {det.confidence * 100:.0f}%"
            (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
            tag_y1 = max(0, y1 - th - baseline - 8)
            tag_y2 = y1 if y1 >= (th + baseline + 8) else y1 + th + baseline + 8
            cv2.rectangle(canvas, (x1, tag_y1), (x1 + tw + 12, tag_y2), bgr_color, -1)
            cv2.putText(
                canvas,
                label,
                (x1 + 6, tag_y2 - baseline - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (15, 20, 25),
                2,
                cv2.LINE_AA,
            )
        return canvas


class DetectionView(QWidget):
    """Detektionsläge (Default): Split-screen för de två videoströmmarna samt Fånga-knapp."""

    capture_requested = Signal(object)  # CapturedFramePair
    model_selection_changed = Signal(str, str)  # family, weights_path
    confidence_changed = Signal(float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._latest_res_1: Optional[StreamFrameResult] = None
        self._latest_res_2: Optional[StreamFrameResult] = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 12)
        main_layout.setSpacing(10)

        # Kontrad med modellval, tröskelvärde och status
        ctrl_frame = QFrame()
        ctrl_frame.setStyleSheet(
            "QFrame { background-color: #18202c; border: 1px solid #2b374b; border-radius: 8px; }"
        )
        ctrl_layout = QHBoxLayout(ctrl_frame)
        ctrl_layout.setContentsMargins(14, 10, 14, 10)
        ctrl_layout.setSpacing(16)

        model_lbl = QLabel("Aktiv detektionsmodell:")
        model_lbl.setStyleSheet("font-weight: bold; color: #cbd5e1; border: none;")
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(340)
        self.model_combo.setStyleSheet(
            "QComboBox { background-color: #0f141b; color: #f8fafc; padding: 6px 10px; border: 1px solid #3b4b64; border-radius: 5px; }"
        )
        self.model_combo.currentIndexChanged.connect(self._on_model_combo_changed)

        conf_lbl = QLabel("Konfidenströskel: 25%")
        conf_lbl.setStyleSheet("color: #cbd5e1; border: none;")
        self.conf_label = conf_lbl
        self.conf_slider = QSlider(Qt.Orientation.Horizontal)
        self.conf_slider.setRange(5, 95)
        self.conf_slider.setValue(25)
        self.conf_slider.setFixedWidth(150)
        self.conf_slider.valueChanged.connect(self._on_conf_slider_changed)

        self.pause_badge = QLabel("● Detektion Aktiv")
        self.pause_badge.setStyleSheet("color: #2ed573; font-weight: bold; border: none;")

        ctrl_layout.addWidget(model_lbl)
        ctrl_layout.addWidget(self.model_combo)
        ctrl_layout.addSpacing(12)
        ctrl_layout.addWidget(conf_lbl)
        ctrl_layout.addWidget(self.conf_slider)
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.pause_badge)

        # Split-screen för de två videoströmmarna
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.panel_1 = VideoStreamPanel(1, "Röntgenström 1 (Vy A)")
        self.panel_2 = VideoStreamPanel(2, "Röntgenström 2 (Vy B)")
        splitter.addWidget(self.panel_1)
        splitter.addWidget(self.panel_2)
        splitter.setSizes([640, 640])

        # Fånga-knapp längst ner för enkel åtkomst i kioskläge
        bottom_bar = QHBoxLayout()
        self.capture_btn = QPushButton("📸  FÅNGA BILDER FÖR TRÄNINGSDATA  (Gå till Annoteringsläge)")
        self.capture_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.capture_btn.setMinimumHeight(54)
        self.capture_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
                padding: 10px 28px;
                border: 1px solid #3b82f6;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton:pressed {
                background-color: #1e40af;
            }
            """
        )
        self.capture_btn.clicked.connect(self.trigger_capture)

        bottom_bar.addStretch()
        bottom_bar.addWidget(self.capture_btn, stretch=2)
        bottom_bar.addStretch()

        main_layout.addWidget(ctrl_frame)
        main_layout.addWidget(splitter, stretch=1)
        main_layout.addLayout(bottom_bar)

    def populate_models(self, models_list: List[Dict[str, str]], active_weights: str = "") -> None:
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        selected_idx = 0
        for idx, item in enumerate(models_list):
            self.model_combo.addItem(item["label"], userData=item)
            if active_weights and item["weights"] == active_weights:
                selected_idx = idx
        self.model_combo.setCurrentIndex(selected_idx)
        self.model_combo.blockSignals(False)

    def _on_model_combo_changed(self, idx: int) -> None:
        if idx < 0:
            return
        data = self.model_combo.itemData(idx)
        if isinstance(data, dict):
            self.model_selection_changed.emit(data["family"], data["weights"])

    def _on_conf_slider_changed(self, val: int) -> None:
        self.conf_label.setText(f"Konfidenströskel: {val}%")
        self.confidence_changed.emit(val / 100.0)

    def set_detection_paused_state(self, paused: bool) -> None:
        if paused:
            self.pause_badge.setText("⏸ Detektion Pausad (Träning pågår)")
            self.pause_badge.setStyleSheet("color: #ffa502; font-weight: bold; border: none;")
        else:
            self.pause_badge.setText("● Detektion Aktiv")
            self.pause_badge.setStyleSheet("color: #2ed573; font-weight: bold; border: none;")

    def update_frames(self, res1: StreamFrameResult, res2: StreamFrameResult) -> None:
        self._latest_res_1 = res1
        self._latest_res_2 = res2
        self.panel_1.update_stream(res1)
        self.panel_2.update_stream(res2)

    def trigger_capture(self) -> None:
        """Fryser aktuella bildrutor och befintliga detektioner från båda strömmarna och öppnar annoteringsläget."""
        if self._latest_res_1 is None or self._latest_res_2 is None:
            return

        pair = CapturedFramePair(
            stream_1_frame=self._latest_res_1.frame_bgr.copy(),
            stream_1_boxes=[b.copy() for b in self._latest_res_1.detections],
            stream_2_frame=self._latest_res_2.frame_bgr.copy(),
            stream_2_boxes=[b.copy() for b in self._latest_res_2.detections],
        )
        self.capture_requested.emit(pair)
