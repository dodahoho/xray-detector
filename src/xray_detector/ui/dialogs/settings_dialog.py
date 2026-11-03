"""Application settings dialog."""

from __future__ import annotations

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
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from xray_detector.config import AppConfig, VideoSourceSettings
from xray_detector.infrastructure.video.device_discovery import list_devices


class VideoSourceEditor(QGroupBox):
    def __init__(self, title: str, settings: VideoSourceSettings) -> None:
        super().__init__(title)
        self._settings = settings
        form = QFormLayout(self)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["device", "file", "test_pattern"])
        self.type_combo.setCurrentText(settings.type)
        form.addRow("Typ:", self.type_combo)

        index_row = QHBoxLayout()
        self.index_spin = QSpinBox()
        self.index_spin.setRange(0, 31)
        self.index_spin.setValue(settings.index)
        index_row.addWidget(self.index_spin)
        self.discover_button = QPushButton("Sök enheter")
        self.discover_button.clicked.connect(self.discover)
        index_row.addWidget(self.discover_button)
        form.addRow("Enhetsindex:", index_row)

        file_row = QHBoxLayout()
        self.file_edit = QLineEdit(settings.file or "")
        file_row.addWidget(self.file_edit)
        browse = QPushButton("...")
        browse.clicked.connect(self.browse)
        file_row.addWidget(browse)
        form.addRow("Videofil:", file_row)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(160, 7680)
        self.width_spin.setValue(settings.width)
        form.addRow("Bredd:", self.width_spin)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(120, 4320)
        self.height_spin.setValue(settings.height)
        form.addRow("Höjd:", self.height_spin)

        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 120)
        self.fps_spin.setValue(settings.fps)
        form.addRow("FPS:", self.fps_spin)

        self.backend_combo = QComboBox()
        self.backend_combo.addItems(["auto", "dshow", "msmf"])
        self.backend_combo.setCurrentText(settings.backend)
        form.addRow("Backend:", self.backend_combo)

        self.loop_check = QCheckBox("Loopa videofil")
        self.loop_check.setChecked(settings.loop_file)
        form.addRow("", self.loop_check)

        self.type_combo.currentTextChanged.connect(self._update_enabled)
        self._update_enabled(self.type_combo.currentText())

    def _update_enabled(self, source_type: str) -> None:
        is_device = source_type == "device"
        is_file = source_type == "file"
        self.index_spin.setEnabled(is_device)
        self.discover_button.setEnabled(is_device)
        self.file_edit.setEnabled(is_file)
        self.width_spin.setEnabled(not is_file)
        self.height_spin.setEnabled(not is_file)
        self.fps_spin.setEnabled(not is_file)
        self.backend_combo.setEnabled(is_device)
        self.loop_check.setEnabled(is_file)

    def discover(self) -> None:
        try:
            devices = list_devices(probe=True)
        except Exception as exc:
            QMessageBox.warning(self, "Enhetssökning", str(exc))
            return
        if not devices:
            QMessageBox.information(self, "Enhetssökning", "Inga videoenheter hittades.")
            return
        names = "\n".join(f"{device.index}: {device.name}" for device in devices)
        QMessageBox.information(self, "Videoenheter", names)

    def browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Välj videofil",
            self.file_edit.text(),
            "Video (*.mp4 *.avi *.mkv *.mov *.wmv);;Alla filer (*)",
        )
        if path:
            self.file_edit.setText(path)

    def apply(self) -> VideoSourceSettings:
        self._settings.type = self.type_combo.currentText()
        self._settings.index = self.index_spin.value()
        self._settings.file = self.file_edit.text().strip() or None
        self._settings.width = self.width_spin.value()
        self._settings.height = self.height_spin.value()
        self._settings.fps = self.fps_spin.value()
        self._settings.backend = self.backend_combo.currentText()
        self._settings.loop_file = self.loop_check.isChecked()
        return self._settings


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Inställningar")
        self.resize(720, 640)

        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs, 1)

        video_tab = QWidget()
        video_layout = QHBoxLayout(video_tab)
        self.cam0_editor = VideoSourceEditor("Kamera 0 / cam0", config.video.cam0)
        self.cam1_editor = VideoSourceEditor("Kamera 1 / cam1", config.video.cam1)
        video_layout.addWidget(self.cam0_editor)
        video_layout.addWidget(self.cam1_editor)
        tabs.addTab(video_tab, "Video")

        detection_tab = QWidget()
        detection_form = QFormLayout(detection_tab)
        self.conf_spin = QDoubleSpinBox()
        self.conf_spin.setRange(0.01, 1.0)
        self.conf_spin.setSingleStep(0.05)
        self.conf_spin.setValue(config.detection.conf)
        detection_form.addRow("Confidence:", self.conf_spin)
        self.iou_spin = QDoubleSpinBox()
        self.iou_spin.setRange(0.01, 1.0)
        self.iou_spin.setSingleStep(0.05)
        self.iou_spin.setValue(config.detection.iou)
        detection_form.addRow("IoU:", self.iou_spin)
        self.imgsz_spin = QSpinBox()
        self.imgsz_spin.setRange(128, 2048)
        self.imgsz_spin.setSingleStep(32)
        self.imgsz_spin.setValue(config.detection.imgsz)
        detection_form.addRow("Bildstorlek:", self.imgsz_spin)
        self.device_edit = QLineEdit(config.detection.device)
        detection_form.addRow("Enhet:", self.device_edit)
        self.half_check = QCheckBox("Halv precision (FP16)")
        self.half_check.setChecked(config.detection.half)
        detection_form.addRow("", self.half_check)
        self.max_fps_spin = QSpinBox()
        self.max_fps_spin.setRange(1, 120)
        self.max_fps_spin.setValue(config.detection.max_fps)
        detection_form.addRow("Max inferens-FPS:", self.max_fps_spin)
        tabs.addTab(detection_tab, "Detektion")

        dataset_tab = QWidget()
        dataset_form = QFormLayout(dataset_tab)
        self.dataset_edit = QLineEdit(config.app.dataset)
        dataset_form.addRow("Datasetnamn:", self.dataset_edit)
        self.jpeg_spin = QSpinBox()
        self.jpeg_spin.setRange(50, 100)
        self.jpeg_spin.setValue(config.dataset.jpeg_quality)
        dataset_form.addRow("JPEG-kvalitet:", self.jpeg_spin)
        self.train_split_spin = QDoubleSpinBox()
        self.train_split_spin.setRange(0.1, 0.95)
        self.train_split_spin.setSingleStep(0.05)
        self.train_split_spin.setValue(config.dataset.train_split)
        dataset_form.addRow("Train split:", self.train_split_spin)
        self.val_split_spin = QDoubleSpinBox()
        self.val_split_spin.setRange(0.05, 0.5)
        self.val_split_spin.setSingleStep(0.05)
        self.val_split_spin.setValue(config.dataset.val_split)
        dataset_form.addRow("Val split:", self.val_split_spin)
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(0, 2_000_000_000)
        self.seed_spin.setValue(config.dataset.split_seed)
        dataset_form.addRow("Split-seed:", self.seed_spin)
        tabs.addTab(dataset_tab, "Dataset")

        ui_tab = QWidget()
        ui_form = QFormLayout(ui_tab)
        self.fullscreen_check = QCheckBox("Starta i fullscreen")
        self.fullscreen_check.setChecked(config.ui.fullscreen)
        ui_form.addRow("", self.fullscreen_check)
        self.kiosk_check = QCheckBox("Kioskläge (dölj meny och avsluta med genväg)")
        self.kiosk_check.setChecked(config.ui.kiosk)
        ui_form.addRow("", self.kiosk_check)
        self.autostart_check = QCheckBox("Starta detektion automatiskt")
        self.autostart_check.setChecked(config.ui.start_detection_on_launch)
        ui_form.addRow("", self.autostart_check)
        self.exit_shortcut_edit = QLineEdit(config.ui.exit_shortcut)
        ui_form.addRow("Avsluta-genväg:", self.exit_shortcut_edit)
        self.cursor_check = QCheckBox("Visa muspekare")
        self.cursor_check.setChecked(config.ui.show_cursor)
        ui_form.addRow("", self.cursor_check)
        tabs.addTab(ui_tab, "Gränssnitt")

        training_tab = QWidget()
        training_form = QFormLayout(training_tab)
        self.training_epochs_spin = QSpinBox()
        self.training_epochs_spin.setRange(1, 2000)
        self.training_epochs_spin.setValue(config.training.epochs)
        training_form.addRow("Epochs:", self.training_epochs_spin)
        self.training_batch_spin = QSpinBox()
        self.training_batch_spin.setRange(1, 512)
        self.training_batch_spin.setValue(config.training.batch)
        training_form.addRow("Batch:", self.training_batch_spin)
        self.training_imgsz_spin = QSpinBox()
        self.training_imgsz_spin.setRange(128, 2048)
        self.training_imgsz_spin.setSingleStep(32)
        self.training_imgsz_spin.setValue(config.training.imgsz)
        training_form.addRow("Bildstorlek:", self.training_imgsz_spin)
        self.training_lr_spin = QDoubleSpinBox()
        self.training_lr_spin.setDecimals(5)
        self.training_lr_spin.setRange(0.00001, 1.0)
        self.training_lr_spin.setValue(config.training.learning_rate)
        training_form.addRow("Learning rate:", self.training_lr_spin)
        self.training_workers_spin = QSpinBox()
        self.training_workers_spin.setRange(0, 64)
        self.training_workers_spin.setValue(config.training.workers)
        training_form.addRow("Workers:", self.training_workers_spin)
        self.training_pause_check = QCheckBox("Pausa detektion under träning")
        self.training_pause_check.setChecked(config.training.pause_detection)
        training_form.addRow("", self.training_pause_check)
        tabs.addTab(training_tab, "Träning")

        note = QLabel(
            "Ändringar i video- och modellinställningar tillämpas nästa gång detektionen startas."
        )
        note.setStyleSheet("color: #858595;")
        layout.addWidget(note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def save(self) -> None:
        if self.train_split_spin.value() + self.val_split_spin.value() > 1.0:
            QMessageBox.warning(self, "Ogiltig split", "Train + val får inte överstiga 1.0.")
            return
        self.cam0_editor.apply()
        self.cam1_editor.apply()
        self.config.detection.conf = self.conf_spin.value()
        self.config.detection.iou = self.iou_spin.value()
        self.config.detection.imgsz = self.imgsz_spin.value()
        self.config.detection.device = self.device_edit.text().strip() or "cuda:0"
        self.config.detection.half = self.half_check.isChecked()
        self.config.detection.max_fps = self.max_fps_spin.value()
        self.config.app.dataset = self.dataset_edit.text().strip() or "default"
        self.config.dataset.jpeg_quality = self.jpeg_spin.value()
        self.config.dataset.train_split = self.train_split_spin.value()
        self.config.dataset.val_split = self.val_split_spin.value()
        self.config.dataset.split_seed = self.seed_spin.value()
        self.config.ui.fullscreen = self.fullscreen_check.isChecked()
        self.config.ui.kiosk = self.kiosk_check.isChecked()
        self.config.ui.start_detection_on_launch = self.autostart_check.isChecked()
        self.config.ui.exit_shortcut = self.exit_shortcut_edit.text().strip() or "Ctrl+Shift+Q"
        self.config.ui.show_cursor = self.cursor_check.isChecked()
        self.config.training.epochs = self.training_epochs_spin.value()
        self.config.training.batch = self.training_batch_spin.value()
        self.config.training.imgsz = self.training_imgsz_spin.value()
        self.config.training.learning_rate = self.training_lr_spin.value()
        self.config.training.workers = self.training_workers_spin.value()
        self.config.training.pause_detection = self.training_pause_check.isChecked()
        self.config.save()
        self.accept()
