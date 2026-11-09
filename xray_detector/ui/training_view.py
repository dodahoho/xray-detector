from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from xray_detector.application.dataset_service import DatasetService
from xray_detector.application.training_service import TrainingService
from xray_detector.domain.config import AppConfig
from xray_detector.domain.training import TrainConfig


class TrainingView(QWidget):
    training_started = Signal()
    training_finished = Signal()
    status_changed = Signal(str)

    def __init__(self, config: AppConfig, dataset: DatasetService, settings, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.dataset_service = dataset
        self.settings = settings
        self.training_service = TrainingService()
        self.worker = None
        layout = QVBoxLayout(self)
        layout.addLayout(self._build_settings())
        layout.addLayout(self._build_export_row())
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log, 1)
        self.refresh_versions()

    def _build_settings(self) -> QFormLayout:
        form = QFormLayout()
        self.model_combo = QComboBox()
        from xray_detector.application.model_registry import MODEL_SPECS

        for spec in MODEL_SPECS:
            self.model_combo.addItem(spec.label, spec.weights)
        form.addRow("Basmodell:", self.model_combo)
        self.version_combo = QComboBox()
        self.version_combo.currentIndexChanged.connect(self._on_version_changed)
        form.addRow("Datasetversion:", self.version_combo)
        self.version_info = QLabel("-")
        form.addRow("", self.version_info)
        self.epochs_spin = QSpinBox()
        self.epochs_spin.setRange(1, 1000)
        self.epochs_spin.setValue(100)
        form.addRow("Epoker:", self.epochs_spin)
        self.imgsz_spin = QSpinBox()
        self.imgsz_spin.setRange(320, 1920)
        self.imgsz_spin.setSingleStep(32)
        self.imgsz_spin.setValue(640)
        form.addRow("Bildstorlek:", self.imgsz_spin)
        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 128)
        self.batch_spin.setValue(16)
        form.addRow("Batch:", self.batch_spin)
        self.start_button = QPushButton("Starta träning")
        self.start_button.setMinimumHeight(40)
        self.start_button.clicked.connect(self._on_start)
        self.abort_button = QPushButton("Avbryt")
        self.abort_button.setEnabled(False)
        self.abort_button.clicked.connect(self._on_abort)
        buttons = QHBoxLayout()
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.abort_button)
        form.addRow(buttons)
        return form

    def _build_export_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        self.export_coco_button = QPushButton("Exportera COCO")
        self.export_coco_button.clicked.connect(self._on_export_coco)
        self.export_yolo_button = QPushButton("Exportera YOLO")
        self.export_yolo_button.clicked.connect(self._on_export_yolo)
        row.addWidget(self.export_coco_button)
        row.addWidget(self.export_yolo_button)
        row.addStretch(1)
        return row

    def restore_settings(self) -> None:
        weights = self.settings.value("training/base_model", type=str)
        if weights:
            index = self.model_combo.findData(weights)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
        for key, spin, default in (
            ("epochs", self.epochs_spin, 100),
            ("imgsz", self.imgsz_spin, 640),
            ("batch", self.batch_spin, 16),
        ):
            value = self.settings.value(f"training/{key}", default, type=int)
            if value:
                spin.setValue(value)
        version = self.settings.value("training/version", type=int)
        if version:
            index = self.version_combo.findData(version)
            if index >= 0:
                self.version_combo.setCurrentIndex(index)

    def save_settings(self) -> None:
        self.settings.setValue("training/base_model", self.model_combo.currentData())
        self.settings.setValue("training/epochs", self.epochs_spin.value())
        self.settings.setValue("training/imgsz", self.imgsz_spin.value())
        self.settings.setValue("training/batch", self.batch_spin.value())
        version = self.version_combo.currentData()
        if version is not None:
            self.settings.setValue("training/version", version)

    def refresh_versions(self) -> None:
        self.version_combo.blockSignals(True)
        self.version_combo.clear()
        for version in self.dataset_service.versions():
            self.version_combo.addItem(f"v{version}", version)
        self.version_combo.blockSignals(False)
        self._on_version_changed()

    def _on_version_changed(self) -> None:
        data = self.version_combo.currentData()
        if data is None:
            self.version_info.setText("-")
            return
        info = self.dataset_service.metadata(data)
        num_train, num_val = self.dataset_service.train_val_counts(int(data))
        self.version_info.setText(
            f"Bilder: {info['num_images']}  Objekt: {info['num_objects']}  "
            f"Train/val: {num_train}/{num_val}  "
            f"Uppdaterad: {info['updated'][:10]}"
        )

    def _current_version(self) -> int | None:
        data = self.version_combo.currentData()
        return None if data is None else int(data)

    def _on_export_coco(self) -> None:
        version = self._current_version()
        if version is None:
            return
        out = self.dataset_service.export_coco(version, self.config.export_dir)
        self.status_changed.emit(f"Exporterade COCO till {out}")

    def _on_export_yolo(self) -> None:
        version = self._current_version()
        if version is None:
            return
        out = self.dataset_service.export_yolo(version, self.config.export_dir)
        self.status_changed.emit(f"Exporterade YOLO till {out}")

    def _on_start(self) -> None:
        version = self._current_version()
        if version is None:
            self.status_changed.emit("Ingen datasetversion vald")
            return
        self.dataset_service.export_yolo(version, self.config.export_dir)
        dataset_yaml = self.config.export_dir / f"v{version}_yolo" / "data.yaml"
        config = TrainConfig(
            dataset_yaml=Path(dataset_yaml),
            weights=self.model_combo.currentData(),
            output_dir=self.config.models_dir / f"v{version}",
            epochs=self.epochs_spin.value(),
            imgsz=self.imgsz_spin.value(),
            batch=self.batch_spin.value(),
        )
        self.worker = self.training_service.create_worker(config)
        self.worker.progress.connect(self.log.appendPlainText)
        self.worker.finished_training.connect(self._on_finished)
        self.start_button.setEnabled(False)
        self.abort_button.setEnabled(True)
        self.log.appendPlainText(
            f"Startar träning: {config.weights} på dataset v{version} "
            f"({config.epochs} epoker, imgsz {config.imgsz}, batch {config.batch})"
        )
        self.worker.start()
        self.training_started.emit()

    def _on_abort(self) -> None:
        if self.worker is not None:
            self.worker.cancel()

    def _on_finished(self, ok: bool, message: str) -> None:
        self.log.appendPlainText(message)
        self.start_button.setEnabled(True)
        self.abort_button.setEnabled(False)
        self.training_finished.emit()
        self.refresh_versions()
