from __future__ import annotations

import copy
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from xray_detector.config import AppConfig, validate_config


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.setWindowTitle("Inställningar")
        self.setMinimumWidth(560)
        self._config = copy.deepcopy(config)

        root = QVBoxLayout(self)

        video_group = QGroupBox("Video")
        video_form = QFormLayout(video_group)
        self.backend = QComboBox()
        self.backend.addItems(["dshow", "msmf", "any"])
        self.backend.setCurrentText(config.video.backend)
        video_form.addRow("Kamerabackend:", self.backend)

        camera_row = QHBoxLayout()
        self.camera_left = QSpinBox()
        self.camera_left.setRange(0, 15)
        self.camera_left.setValue(config.video.camera_left)
        self.camera_right = QSpinBox()
        self.camera_right.setRange(0, 15)
        self.camera_right.setValue(config.video.camera_right)
        camera_row.addWidget(self.camera_left)
        camera_row.addWidget(self.camera_right)
        camera_widget = QWidget()
        camera_widget.setLayout(camera_row)
        video_form.addRow("Kamera vänster/höger:", camera_widget)

        size_row = QHBoxLayout()
        self.width = QSpinBox()
        self.width.setRange(160, 7680)
        self.width.setValue(config.video.width)
        self.height = QSpinBox()
        self.height.setRange(120, 4320)
        self.height.setValue(config.video.height)
        size_row.addWidget(self.width)
        size_row.addWidget(self.height)
        size_widget = QWidget()
        size_widget.setLayout(size_row)
        video_form.addRow("Upplösning (bredd/höjd):", size_widget)

        self.video_fps = QSpinBox()
        self.video_fps.setRange(1, 240)
        self.video_fps.setValue(config.video.fps)
        video_form.addRow("Kamerafps:", self.video_fps)
        self.preview_fps = QSpinBox()
        self.preview_fps.setRange(1, 120)
        self.preview_fps.setValue(config.video.preview_fps)
        video_form.addRow("Visningsfps:", self.preview_fps)
        root.addWidget(video_group)

        detection_group = QGroupBox("Detektion")
        detection_form = QFormLayout(detection_group)
        self.model = QLineEdit(config.detection.model)
        model_row = QHBoxLayout()
        model_row.addWidget(self.model, 1)
        browse = QPushButton("Bläddra...")
        browse.clicked.connect(self._browse_model)
        model_row.addWidget(browse)
        model_widget = QWidget()
        model_widget.setLayout(model_row)
        detection_form.addRow("Modell:", model_widget)

        self.device = QComboBox()
        self.device.setEditable(True)
        self.device.addItems(["auto", "cpu", "0", "1"])
        self.device.setCurrentText(config.detection.device)
        detection_form.addRow("Enhet:", self.device)

        self.confidence = QDoubleSpinBox()
        self.confidence.setRange(0.01, 1.0)
        self.confidence.setSingleStep(0.05)
        self.confidence.setValue(config.detection.confidence)
        detection_form.addRow("Confidence:", self.confidence)

        self.iou = QDoubleSpinBox()
        self.iou.setRange(0.01, 1.0)
        self.iou.setSingleStep(0.05)
        self.iou.setValue(config.detection.iou)
        detection_form.addRow("IoU/NMS:", self.iou)

        self.detection_fps = QDoubleSpinBox()
        self.detection_fps.setRange(0.5, 120.0)
        self.detection_fps.setValue(config.detection.detection_fps)
        detection_form.addRow("Detektioner per sekund:", self.detection_fps)
        root.addWidget(detection_group)

        window_group = QGroupBox("Fönster")
        window_form = QFormLayout(window_group)
        self.fullscreen = QCheckBox("Starta i fullscreen")
        self.fullscreen.setChecked(config.app.fullscreen)
        window_form.addRow(self.fullscreen)
        self.kiosk = QCheckBox("Kioskläge (dölj muspekare)")
        self.kiosk.setChecked(config.app.kiosk)
        window_form.addRow(self.kiosk)
        root.addWidget(window_group)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _browse_model(self) -> None:
        current = self.model.text().strip()
        start = str(Path(current).expanduser().parent) if current else ""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Välj modell",
            start,
            "Modellvikter (*.pt *.onnx);;Alla filer (*)",
        )
        if path:
            self.model.setText(path)

    def _accept(self) -> None:
        config = self._config
        config.video.backend = self.backend.currentText()
        config.video.camera_left = self.camera_left.value()
        config.video.camera_right = self.camera_right.value()
        config.video.width = self.width.value()
        config.video.height = self.height.value()
        config.video.fps = self.video_fps.value()
        config.video.preview_fps = self.preview_fps.value()
        config.detection.model = self.model.text().strip()
        config.detection.device = self.device.currentText().strip() or "auto"
        config.detection.confidence = self.confidence.value()
        config.detection.iou = self.iou.value()
        config.detection.detection_fps = self.detection_fps.value()
        config.app.fullscreen = self.fullscreen.isChecked()
        config.app.kiosk = self.kiosk.isChecked()
        config.app.hide_cursor = self.kiosk.isChecked()
        try:
            validate_config(config)
        except ValueError as exc:
            QMessageBox.warning(self, "Ogiltiga inställningar", str(exc))
            return
        self._config = config
        self.accept()

    def updated_config(self) -> AppConfig:
        return self._config
