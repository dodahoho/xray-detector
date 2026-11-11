from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Signal
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from xray_detector.application.app_config import file_logger, log_path
from xray_detector.application.dataset_service import DatasetService
from xray_detector.application.training_service import TrainingService
from xray_detector.domain.config import AppConfig
from xray_detector.domain.training import TrainConfig
from xray_detector.ui.settings_dialog import TrainingScheduleSection, settings_button
from xray_detector.ui.shortcuts import bind_shortcut, mnemonic, with_hint
from xray_detector.ui.style import button


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
        self.training_log = None
        self.training_service.worker_created.connect(self._on_worker_created)
        self.training_service.scheduler().status_changed.connect(self.status_changed.emit)
        self._activity_filter = _ActivityFilter(self.training_service.scheduler().record_activity)
        QApplication.instance().installEventFilter(self._activity_filter)
        layout = QVBoxLayout(self)
        layout.addLayout(self._build_header())
        layout.addLayout(self._build_settings())
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log, 1)
        self.refresh_dataset_info()
        self._disable_missing_rfdetr()

    def _disable_missing_rfdetr(self) -> None:
        """Avstanger RF-DETR posten nar paketet inte ar installerat."""
        import importlib.util

        if importlib.util.find_spec("rfdetr") is None:
            model = self.model_combo.model()
            for row in range(model.rowCount()):
                spec = self._specs.get(self.model_combo.itemData(row))
                if spec is None or spec.family != "rfdetr":
                    continue
                item = model.item(row)
                item.setEnabled(False)
                self.model_combo.setItemText(
                    row, f"{item.text()} (rfdetr ej installerat)"
                )

    def _build_header(self) -> QHBoxLayout:
        """Inställningsknappen högst upp till höger, som i de andra vyerna."""
        header = QHBoxLayout()
        header.addStretch(1)
        self.settings_button = settings_button(
            self,
            "Inställningar – Träning",
            lambda: [TrainingScheduleSection(self.settings)],
        )
        header.addWidget(self.settings_button)
        return header

    def _build_settings(self) -> QFormLayout:
        form = QFormLayout()
        self.model_combo = QComboBox()
        from xray_detector.application.model_registry import base_models

        self._specs = {}
        for spec in base_models(self.config.models_dir):
            self.model_combo.addItem(spec.label, spec.key)
            self._specs[spec.key] = spec
        form.addRow("Basmodell:", self.model_combo)
        self.dataset_info = QLabel("-")
        form.addRow("Dataset:", self.dataset_info)
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
        self.run_combo = QComboBox()
        self.run_combo.addItem("Direkt", "direct")
        self.run_combo.addItem("Nattetid (schema)", "night")
        self.run_combo.addItem("Efter inaktivitet", "inactivity")
        form.addRow("Kör:", self.run_combo)
        self.start_button = button(mnemonic("Starta träning", "R"), primary=True)
        self.start_button.clicked.connect(self._on_start)
        self.abort_button = button(with_hint("Avbryt", "Esc"))
        self.abort_button.setEnabled(False)
        self.abort_button.clicked.connect(self._on_abort)
        buttons = QHBoxLayout()
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.abort_button)
        form.addRow(buttons)
        bind_shortcut(self, "Esc", self._on_abort)
        return form

    def restore_settings(self) -> None:
        saved = self.settings.value("training/base_model", type=str)
        if saved:
            index = self.model_combo.findData(saved)
            if index < 0:
                # Äldre versioner sparade viktfilens namn, t.ex. yolo26m.pt
                index = self.model_combo.findData(Path(saved).stem)
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

    def save_settings(self) -> None:
        self.settings.setValue("training/base_model", self.model_combo.currentData())
        self.settings.setValue("training/epochs", self.epochs_spin.value())
        self.settings.setValue("training/imgsz", self.imgsz_spin.value())
        self.settings.setValue("training/batch", self.batch_spin.value())

    def refresh_dataset_info(self) -> None:
        """Visar sammanställningen för datasetet som träningen utgår från."""
        info = self.dataset_service.metadata()
        num_train, num_val = self.dataset_service.train_val_counts()
        self.dataset_info.setText(
            f"Bilder: {info['num_images']}  Objekt: {info['num_objects']}  "
            f"Train/val: {num_train}/{num_val}  "
            f"Uppdaterad: {info['updated'][:10]}"
        )

    def _on_start(self) -> None:
        import importlib.util

        if self.dataset_service.metadata()["num_images"] == 0:
            self.status_changed.emit("Datasetet är tomt")
            return
        spec = self._specs.get(self.model_combo.currentData())
        if spec is None:
            self.status_changed.emit("Ingen basmodell vald")
            return
        weights = spec.weights
        family = spec.family
        if family == "rfdetr":
            if importlib.util.find_spec("rfdetr") is None:
                self.status_changed.emit(
                    "RF-DETR kraver rfdetr-paketet (uv sync --extra rfdetr)"
                )
                return
            dataset_path = self.dataset_service.export_rfdetr(self.config.export_dir)
        else:
            self.dataset_service.export_yolo(self.config.export_dir)
            dataset_path = self.config.export_dir / "yolo" / "data.yaml"
        config = TrainConfig(
            dataset_yaml=Path(dataset_path),
            weights=weights,
            output_dir=self.config.trained_dir / datetime.now().strftime("%Y-%m-%d_%H%M%S"),
            epochs=self.epochs_spin.value(),
            imgsz=self.imgsz_spin.value(),
            batch=self.batch_spin.value(),
            family=family,
        )
        run_mode = self.run_combo.currentData()
        if run_mode == "direct":
            self.training_service.create_worker(config)
            return
        scheduler = self.training_service.scheduler()
        scheduler.queue_job(
            config,
            run_mode,
            inactivity_minutes=int(self.settings.value("training/inactivity_minutes", 30, type=int)),
            night_start=str(self.settings.value("training/night_start", "23:00")),
            night_end=str(self.settings.value("training/night_end", "05:00")),
        )

    def _on_worker_created(self, worker) -> None:
        """Kopplar en (direkt eller schemalagd) worker till loggen och startar den."""
        self.worker = worker
        self.training_log = file_logger(
            "xray.training", log_path(self.config.logs_dir, "training")
        )
        worker.progress.connect(self._on_progress)
        worker.finished_training.connect(self._on_finished)
        self.start_button.setEnabled(False)
        self.abort_button.setEnabled(True)
        header = (
            f"Startar träning: {worker.config.weights} på {worker.config.dataset_yaml} "
            f"({worker.config.epochs} epoker, imgsz {worker.config.imgsz}, batch {worker.config.batch}) "
            f"-> {worker.config.output_dir}"
        )
        self.log.appendPlainText(header)
        self.training_log.info("=== %s ===", header)
        worker.start()
        self.training_started.emit()

    def _on_progress(self, line: str) -> None:
        """Visar träningsprocessens rad och skriver den till logs/training.log."""
        self.log.appendPlainText(line)
        if self.training_log is not None:
            self.training_log.info(line)

    def _on_abort(self) -> None:
        if self.worker is not None and self.worker.is_running():
            self.training_service.cancel()
        elif self.training_service.scheduler().has_queued():
            self.training_service.scheduler().cancel()

    def active_worker(self):
        return self.worker

    def _on_finished(self, ok: bool, message: str) -> None:
        self.log.appendPlainText(message)
        if self.training_log is not None:
            self.training_log.info(message)
        self.start_button.setEnabled(True)
        self.abort_button.setEnabled(False)
        self.training_finished.emit()
        self.refresh_dataset_info()


class _ActivityFilter(QObject):
    """Globalt mus-/tangentfilter som rapporterar användaraktivitet."""

    def __init__(self, on_activity, parent=None) -> None:
        super().__init__(parent)
        self._on_activity = on_activity

    def eventFilter(self, obj, event) -> bool:
        if event.type() in (
            QEvent.Type.MouseMove,
            QEvent.Type.MouseButtonPress,
            QEvent.Type.KeyPress,
            QEvent.Type.Wheel,
        ):
            self._on_activity()
        return False
