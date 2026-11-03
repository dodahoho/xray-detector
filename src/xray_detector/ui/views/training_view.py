"""Training mode view."""

from __future__ import annotations

import logging

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from xray_detector.application.dataset_service import DatasetService
from xray_detector.application.model_registry import ModelRegistry
from xray_detector.application.training_service import TrainingService
from xray_detector.config import AppConfig
from xray_detector.domain.training import TrainingParams, TrainingRequest

logger = logging.getLogger(__name__)


class TrainingView(QWidget):
    training_about_to_start = Signal()
    training_finished = Signal(bool, str)

    def __init__(
        self,
        config: AppConfig,
        dataset_service: DatasetService,
        model_registry: ModelRegistry,
        training_service: TrainingService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.config = config
        self.dataset_service = dataset_service
        self.model_registry = model_registry
        self.training_service = training_service

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        form_group = QGroupBox("Träningsinställningar")
        form = QFormLayout(form_group)

        self.dataset_combo = QComboBox()
        form.addRow("Dataset:", self.dataset_combo)
        self.version_combo = QComboBox()
        form.addRow("Version:", self.version_combo)
        self.base_model_combo = QComboBox()
        form.addRow("Basmodell:", self.base_model_combo)
        self.run_name_edit = QLineEdit("run")
        form.addRow("Körningsnamn:", self.run_name_edit)

        self.epochs_spin = QSpinBox()
        self.epochs_spin.setRange(1, 2000)
        self.epochs_spin.setValue(config.training.epochs)
        form.addRow("Epochs:", self.epochs_spin)

        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 512)
        self.batch_spin.setValue(config.training.batch)
        form.addRow("Batch:", self.batch_spin)

        self.imgsz_spin = QSpinBox()
        self.imgsz_spin.setRange(128, 2048)
        self.imgsz_spin.setSingleStep(32)
        self.imgsz_spin.setValue(config.training.imgsz)
        form.addRow("Bildstorlek:", self.imgsz_spin)

        self.lr_spin = QDoubleSpinBox()
        self.lr_spin.setDecimals(5)
        self.lr_spin.setRange(0.00001, 1.0)
        self.lr_spin.setSingleStep(0.001)
        self.lr_spin.setValue(config.training.learning_rate)
        form.addRow("Learning rate:", self.lr_spin)

        self.patience_spin = QSpinBox()
        self.patience_spin.setRange(0, 1000)
        self.patience_spin.setValue(config.training.patience)
        form.addRow("Patience:", self.patience_spin)

        self.workers_spin = QSpinBox()
        self.workers_spin.setRange(0, 64)
        self.workers_spin.setValue(config.training.workers)
        form.addRow("Workers:", self.workers_spin)

        self.device_edit = QLineEdit(config.detection.device)
        form.addRow("Enhet:", self.device_edit)

        self.pause_check = QCheckBox("Pausa detektionen under träning")
        self.pause_check.setChecked(config.training.pause_detection)
        form.addRow("", self.pause_check)

        self.start_button = QPushButton("Starta träning")
        self.start_button.setStyleSheet(
            "QPushButton { background-color: #2f5f9e; color: white; font-weight: bold; "
            "padding: 7px 16px; border-radius: 4px; }"
        )
        self.start_button.clicked.connect(self.start_training)
        self.stop_button = QPushButton("Stoppa")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_training)
        buttons = QHBoxLayout()
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.stop_button)
        form.addRow("", buttons)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        form.addRow("", self.progress)

        form_group.setMaximumWidth(420)
        layout.addWidget(form_group)

        log_group = QGroupBox("Logg")
        log_layout = QVBoxLayout(log_group)
        self.status_label = QLabel("Ingen träning pågår")
        log_layout.addWidget(self.status_label)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(5000)
        self.log_view.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
        log_layout.addWidget(self.log_view, 1)
        layout.addWidget(log_group, 1)

        self.dataset_combo.currentTextChanged.connect(self.refresh_versions)
        self.training_service.log.connect(self.append_log)
        self.training_service.finished.connect(self._on_training_finished)

        self.refresh_datasets()
        self.refresh_models()

    def refresh_datasets(self) -> None:
        current = self.dataset_combo.currentText()
        datasets = self.dataset_service.list_datasets()
        self.dataset_combo.blockSignals(True)
        try:
            self.dataset_combo.clear()
            self.dataset_combo.addItems(datasets)
            if current in datasets:
                self.dataset_combo.setCurrentText(current)
            elif self.config.app.dataset in datasets:
                self.dataset_combo.setCurrentText(self.config.app.dataset)
        finally:
            self.dataset_combo.blockSignals(False)
        self.refresh_versions()

    def refresh_versions(self) -> None:
        name = self.dataset_combo.currentText()
        self.version_combo.clear()
        if not name:
            return
        try:
            versions = self.dataset_service.list_versions(name)
        except Exception as exc:
            logger.warning("Could not list versions: %s", exc)
            return
        for summary in versions:
            self.version_combo.addItem(
                f"{summary.version}  ({summary.image_count} bilder, "
                f"{summary.annotation_count} objekt, {summary.created_at})",
                summary.version,
            )
        if versions:
            self.version_combo.setCurrentIndex(len(versions) - 1)

    def refresh_models(self) -> None:
        current = self.base_model_combo.currentData()
        self.base_model_combo.clear()
        for model in self.model_registry.base_models():
            self.base_model_combo.addItem(f"{model.name} [{model.family}]", model.id)
        if current:
            index = self.base_model_combo.findData(current)
            if index >= 0:
                self.base_model_combo.setCurrentIndex(index)

    def _build_request(self) -> TrainingRequest | None:
        dataset = self.dataset_combo.currentText()
        version = self.version_combo.currentData()
        model_id = self.base_model_combo.currentData()
        if not dataset or not version or not model_id:
            QMessageBox.warning(
                self, "Ofullständigt underlag", "Välj dataset, version och basmodell."
            )
            return None
        try:
            summary = self.dataset_service.version_summary(str(version), dataset)
        except FileNotFoundError as exc:
            QMessageBox.warning(self, "Version saknas", str(exc))
            return None
        if summary.pair_count < 2:
            QMessageBox.warning(
                self,
                "För litet dataset",
                "Träning kräver minst två bildpar så att både train och val får data.",
            )
            return None
        model = self.model_registry.get(str(model_id))
        base_model_path = model.path
        if base_model_path.exists():
            base_model_path = base_model_path.resolve()
        params = TrainingParams(
            epochs=self.epochs_spin.value(),
            batch=self.batch_spin.value(),
            imgsz=self.imgsz_spin.value(),
            learning_rate=self.lr_spin.value(),
            patience=self.patience_spin.value(),
            workers=self.workers_spin.value(),
            device=self.device_edit.text().strip() or "cuda:0",
        )
        return TrainingRequest(
            dataset_name=dataset,
            dataset_version=str(version),
            base_model_id=model.id,
            base_model_path=str(base_model_path),
            family=model.family,
            params=params,
            run_name=self.run_name_edit.text().strip() or "run",
            pause_detection=self.pause_check.isChecked(),
        )

    def start_training(self) -> None:
        if self.training_service.is_running:
            return
        request = self._build_request()
        if request is None:
            return
        if request.pause_detection:
            self.training_about_to_start.emit()
        self.append_log(
            f"Förbereder träning: dataset={request.dataset_name} {request.dataset_version}, "
            f"modell={request.base_model_id}, family={request.family}"
        )
        ok, message = self.training_service.start(request)
        if not ok:
            self.append_log(message)
            QMessageBox.critical(self, "Kunde inte starta träning", message)
            self.training_finished.emit(False, message)
            return
        self._set_running(True)
        self.status_label.setText("Träning pågår...")

    def stop_training(self) -> None:
        self.training_service.stop()

    def _set_running(self, running: bool) -> None:
        self.start_button.setEnabled(not running)
        self.stop_button.setEnabled(running)
        for widget in (
            self.dataset_combo,
            self.version_combo,
            self.base_model_combo,
            self.run_name_edit,
            self.epochs_spin,
            self.batch_spin,
            self.imgsz_spin,
            self.lr_spin,
            self.patience_spin,
            self.workers_spin,
            self.device_edit,
            self.pause_check,
        ):
            widget.setEnabled(not running)
        self.progress.setRange(0, 0 if running else 1)
        self.progress.setValue(0)

    def append_log(self, text: str) -> None:
        if not text:
            return
        self.log_view.appendPlainText(text.rstrip())
        scrollbar = self.log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_training_finished(self, success: bool, message: str, _details=None) -> None:
        self._set_running(False)
        self.status_label.setText(message)
        self.append_log(message)
        self.model_registry.refresh()
        self.refresh_models()
        if success:
            QMessageBox.information(self, "Träning klar", message)
        else:
            QMessageBox.warning(self, "Träning misslyckades", message)
        self.training_finished.emit(success, message)
