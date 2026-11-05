from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from PySide6.QtCore import QProcess, QProcessEnvironment, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
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

from xray_detector.config import AppConfig
from xray_detector.dataset.store import DatasetStore, list_dataset_metadata
from xray_detector.detection.ultralytics_backend import ultralytics_available
from xray_detector.training.trainer import (
    TrainingParameters,
    TrainingPlan,
    finalize_training,
    prepare_training,
)
from xray_detector.util.paths import AppPaths

LOGGER = logging.getLogger(__name__)


def _source_root() -> Path:
    return Path(__file__).resolve().parents[2]


class TrainingView(QWidget):
    trainingStarted = Signal()
    trainingFinished = Signal(bool, str)
    modelCreated = Signal(str)
    statusMessage = Signal(str)

    def __init__(self, config: AppConfig, paths: AppPaths, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.config = config
        self.paths = paths
        self._process: QProcess | None = None
        self._plan: TrainingPlan | None = None
        self._stop_requested = False
        self._running = False
        self._finishing = False
        self._kill_timer: QTimer | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        title = QLabel("Träning")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        root.addWidget(title)

        group = QGroupBox("Träningsjobb")
        form = QFormLayout(group)

        model_row = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.setMinimumWidth(320)
        model_row.addWidget(self.model_combo, 1)
        browse = QPushButton("Bläddra...")
        browse.clicked.connect(self._browse_model)
        model_row.addWidget(browse)
        model_widget = QWidget()
        model_widget.setLayout(model_row)
        form.addRow("Basmodell:", model_widget)

        self.dataset_combo = QComboBox()
        form.addRow("Dataset:", self.dataset_combo)

        self.epochs = QSpinBox()
        self.epochs.setRange(1, 10000)
        self.epochs.setValue(config.training.epochs)
        form.addRow("Epochs:", self.epochs)

        self.imgsz = QSpinBox()
        self.imgsz.setRange(64, 4096)
        self.imgsz.setSingleStep(32)
        self.imgsz.setValue(config.training.imgsz)
        form.addRow("Bildstorlek:", self.imgsz)

        self.batch = QSpinBox()
        self.batch.setRange(1, 512)
        self.batch.setValue(config.training.batch)
        form.addRow("Batch:", self.batch)

        self.learning_rate = QDoubleSpinBox()
        self.learning_rate.setDecimals(5)
        self.learning_rate.setRange(0.00001, 1.0)
        self.learning_rate.setSingleStep(0.001)
        self.learning_rate.setValue(0.01)
        form.addRow("Learning rate:", self.learning_rate)

        self.device = QComboBox()
        self.device.setEditable(True)
        self.device.addItems(["auto", "cpu", "0", "1"])
        form.addRow("Enhet:", self.device)

        self.workers = QSpinBox()
        self.workers.setRange(0, 32)
        self.workers.setValue(config.training.workers)
        form.addRow("Dataloader-workers:", self.workers)

        self.seed = QSpinBox()
        self.seed.setRange(0, 999999)
        self.seed.setValue(0)
        form.addRow("Seed:", self.seed)
        root.addWidget(group)

        controls = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        controls.addWidget(self.progress, 1)
        self.start_button = QPushButton("Starta träning")
        self.start_button.clicked.connect(self._start)
        controls.addWidget(self.start_button)
        self.stop_button = QPushButton("Stoppa")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self._stop)
        controls.addWidget(self.stop_button)
        root.addLayout(controls)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(5000)
        self.log.setStyleSheet("font-family: Consolas, monospace;")
        root.addWidget(self.log, 1)

    def showEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().showEvent(event)
        if not self._running:
            self.refresh_datasets()
            self.refresh_models()

    def apply_config(self, config: AppConfig) -> None:
        self.config = config
        if not self._running:
            self.epochs.setValue(config.training.epochs)
            self.imgsz.setValue(config.training.imgsz)
            self.batch.setValue(config.training.batch)
            self.workers.setValue(config.training.workers)
            self.refresh_models()
            self.refresh_datasets()

    def refresh_models(self) -> None:
        from xray_detector.detection.registry import available_models

        current = self.model_combo.currentText().strip()
        self.model_combo.clear()
        for model in available_models(self.paths.models):
            label = model.model_id
            if model.description:
                label = f"{label} — {model.description}"
            self.model_combo.addItem(label, str(model.path))
        default = current or self.config.training.default_base_model
        index = self.model_combo.findData(default)
        if index < 0:
            index = self.model_combo.findText(default)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
        else:
            self.model_combo.setEditText(default)

    def refresh_datasets(self) -> None:
        current = self.dataset_combo.currentData()
        self.dataset_combo.clear()
        datasets = list_dataset_metadata(self.paths.datasets)
        for metadata in datasets:
            label = (
                f"{metadata.dataset_id} · v{metadata.version} · "
                f"{metadata.image_count} bilder · {metadata.annotation_count} annoteringar"
            )
            self.dataset_combo.addItem(label, metadata.dataset_id)
        preferred = current or self.config.app.active_dataset
        index = self.dataset_combo.findData(preferred)
        if index >= 0:
            self.dataset_combo.setCurrentIndex(index)
        self.start_button.setEnabled(bool(datasets) and not self._running)

    def _browse_model(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Välj basmodell", "", "Modellvikter (*.pt);;Alla filer (*)"
        )
        if path:
            self.model_combo.setEditText(path)

    def _set_running(self, running: bool) -> None:
        self._running = running
        self.start_button.setEnabled(not running and self.dataset_combo.count() > 0)
        self.stop_button.setEnabled(running)
        self.model_combo.setEnabled(not running)
        self.dataset_combo.setEnabled(not running)
        self.epochs.setEnabled(not running)
        self.imgsz.setEnabled(not running)
        self.batch.setEnabled(not running)
        self.learning_rate.setEnabled(not running)
        self.device.setEnabled(not running)
        self.workers.setEnabled(not running)
        self.seed.setEnabled(not running)

    def _start(self) -> None:
        if self._running:
            return
        if not ultralytics_available():
            QMessageBox.critical(
                self,
                "Ultralytics saknas",
                "Ultralytics är inte installerat.\n\nKör: uv sync --extra detection",
            )
            return
        dataset_id = self.dataset_combo.currentData()
        if not dataset_id:
            QMessageBox.warning(self, "Träning", "Välj ett dataset.")
            return
        model_path = self.model_combo.currentData()
        base_model = self.model_combo.currentText().strip()
        if model_path and self.model_combo.currentText() == self.model_combo.itemText(self.model_combo.currentIndex()):
            base_model = str(model_path)
        if not base_model:
            QMessageBox.warning(self, "Träning", "Välj en basmodell.")
            return

        parameters = TrainingParameters(
            epochs=self.epochs.value(),
            imgsz=self.imgsz.value(),
            batch=self.batch.value(),
            learning_rate=self.learning_rate.value(),
            device=self.device.currentText().strip() or "auto",
            workers=self.workers.value(),
            seed=self.seed.value(),
        )
        store = DatasetStore(self.paths.datasets, str(dataset_id))
        try:
            self._plan = prepare_training(
                store,
                base_model,
                self.paths.training,
                parameters,
            )
        except Exception as exc:
            LOGGER.exception("Kunde inte förbereda träning")
            QMessageBox.critical(self, "Träning", f"Kunde inte förbereda träningen:\n{exc}")
            return

        self.log.clear()
        self._append_log(f"Dataset: {dataset_id} v{self._plan.dataset_metadata.version}")
        self._append_log(
            f"Train/val-bilder: {self._plan.dataset_info.train_images}/"
            f"{self._plan.dataset_info.val_images}"
        )
        self._append_log(" ".join(self._plan.command))
        self.progress.setRange(0, 0)
        self._stop_requested = False
        self._finishing = False
        self._set_running(True)
        self.trainingStarted.emit()

        process = QProcess(self)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        environment = QProcessEnvironment.systemEnvironment()
        existing = environment.value("PYTHONPATH")
        source = str(_source_root())
        environment.insert("PYTHONPATH", source + (os.pathsep + existing if existing else ""))
        process.setProcessEnvironment(environment)
        process.setWorkingDirectory(str(self._plan.run_dir))
        process.readyReadStandardOutput.connect(self._read_output)
        process.finished.connect(self._finished)
        process.errorOccurred.connect(self._process_error)
        self._process = process
        program, *arguments = self._plan.command
        process.setProgram(program)
        process.setArguments(arguments)
        process.start()
        self.statusMessage.emit("Träning startad – detektionen är pausad.")

    def _read_output(self) -> None:
        if self._process is None:
            return
        data = bytes(self._process.readAllStandardOutput())
        text = data.decode("utf-8", errors="replace")
        if text:
            self._append_log(text.rstrip("\r\n"))

    def _append_log(self, text: str) -> None:
        self.log.appendPlainText(text)
        scrollbar = self.log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _process_error(self, error) -> None:  # type: ignore[no-untyped-def]
        if error == QProcess.ProcessError.FailedToStart:
            self._append_log("Kunde inte starta träningsprocessen.")
            self._finish(False, "Kunde inte starta träningsprocessen.")

    def _finished(self, exit_code: int, exit_status) -> None:  # type: ignore[no-untyped-def]
        if self._finishing:
            return
        self._read_output()
        if self._stop_requested:
            self._finish(False, "Träningen stoppades av användaren.")
            return
        if exit_code != 0:
            self._finish(False, f"Träningen misslyckades (exitkod {exit_code}). Se loggen.")
            return
        if self._plan is None:
            self._finish(False, "Ingen träningsplan finns.")
            return
        try:
            metadata, weights = finalize_training(self._plan, self.paths.models)
        except Exception as exc:
            LOGGER.exception("Kunde inte slutföra träningen")
            self._finish(False, f"Träningen blev klar men modellen kunde inte sparas: {exc}")
            return
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        message = (
            f"Modell sparad: {weights} (dataset {metadata.dataset_id} "
            f"v{metadata.dataset_version})"
        )
        self._append_log(message)
        self._finishing = True
        self._set_running(False)
        self._cleanup_process()
        self._plan = None
        self.refresh_models()
        self.modelCreated.emit(str(weights))
        self.trainingFinished.emit(True, message)
        self.statusMessage.emit(message)

    def _finish(self, success: bool, message: str) -> None:
        if self._finishing:
            return
        self._finishing = True
        self.progress.setRange(0, 100)
        if not success:
            self.progress.setValue(0)
        self._append_log(message)
        self._set_running(False)
        self._cleanup_process()
        self._plan = None
        self.refresh_datasets()
        self.trainingFinished.emit(success, message)
        self.statusMessage.emit(message)

    def _cleanup_process(self) -> None:
        if self._process is not None:
            self._process.deleteLater()
            self._process = None
        if self._kill_timer is not None:
            self._kill_timer.stop()
            self._kill_timer = None

    def _stop(self) -> None:
        if self._process is None:
            return
        self._stop_requested = True
        self._append_log("Stoppar träningen...")
        self._process.terminate()
        self._kill_timer = QTimer(self)
        self._kill_timer.setSingleShot(True)
        self._kill_timer.timeout.connect(self._force_kill)
        self._kill_timer.start(5000)

    def _force_kill(self) -> None:
        if self._process is not None and self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.kill()

    def shutdown(self) -> None:
        if self._process is not None:
            self._stop_requested = True
            self._process.terminate()
            self._process.waitForFinished(3000)
            if self._process.state() != QProcess.ProcessState.NotRunning:
                self._process.kill()
                self._process.waitForFinished(1000)
