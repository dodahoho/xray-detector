from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from xray_detector.application.app_config import file_logger, log_path
from xray_detector.application.dataset_service import DatasetService
from xray_detector.application.training_history import run_epochs
from xray_detector.application.training_service import TrainingService
from xray_detector.domain.config import AppConfig
from xray_detector.domain.model_input import DEFAULT_SIZE, MAX_SIZE, MIN_SIZE, STEP
from xray_detector.domain.training import TrainConfig, imgsz_for
from xray_detector.ui.settings_dialog import (
    TrainValSplitSection,
    TrainingScheduleSection,
    settings_button,
    train_ratio,
)
from xray_detector.ui.shortcuts import bind_shortcut, mnemonic, with_hint
from xray_detector.ui.style import FormCard, button
from xray_detector.ui.training_chart import TrainingChart
from xray_detector.ui.training_history import TrainingHistoryView


def _format_image_sizes(sizes: list[tuple[int, int, int]]) -> str:
    """Datasetets upplösningar som "1920x1080 (12), 1280x720 (3)" (TASK-80)."""
    if not sizes:
        return "Datasetets upplösningar: -"
    listed = ", ".join(f"{width}x{height} ({count})" for width, height, count in sizes)
    return f"Datasetets upplösningar: {listed}"


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
        # bildstorleken följer datasetet tills användaren väljer en egen (TASK-80)
        self._imgsz_user_set = False
        self._applying_imgsz = False
        self.training_service.worker_created.connect(self._on_worker_created)
        self.training_service.scheduler().status_changed.connect(self.status_changed.emit)
        self._activity_filter = _ActivityFilter(self.training_service.scheduler().record_activity)
        QApplication.instance().installEventFilter(self._activity_filter)
        layout = QVBoxLayout(self)
        layout.addLayout(self._build_header())
        # kortet håller sig till vänster, så fälten inte växer över skärmen (TASK-82)
        layout.addWidget(self._build_settings(), 0, Qt.AlignmentFlag.AlignLeft)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Ingen träning")
        layout.addWidget(self.progress_bar)
        self.epoch_label = QLabel("Ingen träning pågår")
        layout.addWidget(self.epoch_label)
        self.chart = TrainingChart()
        # diagramytorna syns bara när det finns något att visa (TASK-70)
        self.chart.setVisible(False)
        layout.addWidget(self.chart, 2)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.history = TrainingHistoryView(self.config.trained_dir)
        self.history.run_selected.connect(self._on_history_selected)
        self.bottom_tabs = QTabWidget()
        self.bottom_tabs.addTab(self.log, "Logg")
        self.bottom_tabs.addTab(self.history, "Tidigare träningar")
        layout.addWidget(self.bottom_tabs, 1)
        self.refresh_dataset_info()

    def refresh_models(self) -> None:
        """Bygger om basmodellistan ur katalogen och behåller valet (TASK-81)."""
        from xray_detector.application.model_registry import base_models

        current = self.model_combo.currentData()
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self._specs = {}
        for spec in base_models(self.config.models_dir):
            self.model_combo.addItem(spec.label, spec.key)
            self._specs[spec.key] = spec
        self._disable_missing_rfdetr()
        index = self.model_combo.findData(current)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
        self.model_combo.blockSignals(False)

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
            self, "Inställningar – Träning", self._settings_sections
        )
        header.addWidget(self.settings_button)
        return header

    def _settings_sections(self) -> list:
        """Träningsschemat och train/val-delningen (TASK-7, TASK-72)."""
        split = TrainValSplitSection(self.settings)
        # redovisningen i vyn följer andelen medan dialogen är öppen
        split.ratio_changed.connect(self.refresh_dataset_info)
        return [TrainingScheduleSection(self.settings), split]

    def _build_settings(self) -> FormCard:
        """Träningsinställningarna i ett kort med maxbredd (TASK-82)."""
        card = FormCard("Träningsinställningar")
        form = card.form
        self.model_combo = QComboBox()
        self.refresh_models()
        form.addRow("Basmodell:", self.model_combo)
        self.dataset_info = QLabel("-")
        # sammanställningen kan bli lång; den radbryts i stället för att klippas
        self.dataset_info.setWordWrap(True)
        form.addRow("Dataset:", self.dataset_info)
        self.epochs_spin = QSpinBox()
        self.epochs_spin.setRange(1, 1000)
        self.epochs_spin.setValue(100)
        form.addRow("Epoker:", self.epochs_spin)
        self.imgsz_spin = QSpinBox()
        self.imgsz_spin.setRange(MIN_SIZE, MAX_SIZE)
        self.imgsz_spin.setSingleStep(STEP)
        self.imgsz_spin.setValue(DEFAULT_SIZE)
        self.imgsz_spin.valueChanged.connect(self._on_imgsz_changed)
        form.addRow("Bildstorlek:", self.imgsz_spin)
        # upplösningarna får en egen rad, annars klipps listan i ett smalt kort
        self.imgsz_info = QLabel("-")
        self.imgsz_info.setStyleSheet("color: #888;")
        self.imgsz_info.setWordWrap(True)
        form.addRow(self.imgsz_info)
        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 128)
        self.batch_spin.setValue(16)
        form.addRow("Batch:", self.batch_spin)
        self.run_combo = QComboBox()
        self.run_combo.addItem("Direkt", "direct")
        self.run_combo.addItem("Nattetid (schema)", "night")
        self.run_combo.addItem("Efter inaktivitet", "inactivity")
        form.addRow("Kör:", self.run_combo)
        self.overfitting_check = QCheckBox("Avbryt vid överträning")
        self.overfitting_check.setChecked(True)
        self.overfitting_check.setToolTip(
            "Avbryter träningen när train-loss fortsätter sjunka medan val-mAP vänder ner"
        )
        form.addRow("Överträning:", self.overfitting_check)
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
        return card

    def _on_imgsz_changed(self, _value: int) -> None:
        """Ett eget val stannar kvar när datasetet ändras (TASK-80)."""
        if not self._applying_imgsz:
            self._imgsz_user_set = True

    def _set_imgsz(self, value: int, user: bool) -> None:
        """Sätter storleken utan att den räknas som ett användarval."""
        self._applying_imgsz = True
        self.imgsz_spin.setValue(value)
        self._applying_imgsz = False
        self._imgsz_user_set = user

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
            ("batch", self.batch_spin, 16),
        ):
            value = self.settings.value(f"training/{key}", default, type=int)
            if value:
                spin.setValue(value)
        # utan sparat val fortsätter storleken att följa datasetet (TASK-80)
        saved_imgsz = self.settings.value("training/imgsz", type=int)
        if saved_imgsz:
            self._set_imgsz(saved_imgsz, user=True)
        self.overfitting_check.setChecked(
            self.settings.value("training/overfitting_guard", True, type=bool)
        )

    def save_settings(self) -> None:
        self.settings.setValue("training/base_model", self.model_combo.currentData())
        self.settings.setValue("training/epochs", self.epochs_spin.value())
        if self._imgsz_user_set:
            self.settings.setValue("training/imgsz", self.imgsz_spin.value())
        self.settings.setValue("training/batch", self.batch_spin.value())
        self.settings.setValue(
            "training/overfitting_guard", self.overfitting_check.isChecked()
        )

    def refresh_dataset_info(self) -> None:
        """Visar sammanställningen för datasetet som träningen utgår från.

        Train/val räknas i bildpar, eftersom delningen sker per fångstgrupp (TASK-72).
        Bildstorlekens default följer datasetets vanligaste upplösning (TASK-80).
        """
        info = self.dataset_service.metadata()
        num_train, num_val = self.dataset_service.train_val_counts(
            train_ratio(self.settings)
        )
        self.dataset_info.setText(
            f"Bilder: {info['num_images']}  Objekt: {info['num_objects']}  "
            f"Train/val: {num_train}/{num_val} par  "
            f"Uppdaterad: {info['updated'][:10]}"
        )
        sizes = self.dataset_service.image_sizes()
        self.imgsz_info.setText(_format_image_sizes(sizes))
        if sizes and not self._imgsz_user_set:
            self._set_imgsz(imgsz_for(sizes[0][0], sizes[0][1]), user=False)

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
        ratio = train_ratio(self.settings)
        if family == "rfdetr":
            if importlib.util.find_spec("rfdetr") is None:
                self.status_changed.emit(
                    "RF-DETR kraver rfdetr-paketet (uv sync --extra rfdetr)"
                )
                return
            dataset_path = self.dataset_service.export_rfdetr(
                self.config.export_dir, ratio
            )
        else:
            self.dataset_service.export_yolo(self.config.export_dir, ratio)
            dataset_path = self.config.export_dir / "yolo" / "data.yaml"
        config = TrainConfig(
            dataset_yaml=Path(dataset_path),
            weights=weights,
            output_dir=self.config.trained_dir / datetime.now().strftime("%Y-%m-%d_%H%M%S"),
            epochs=self.epochs_spin.value(),
            imgsz=self.imgsz_spin.value(),
            batch=self.batch_spin.value(),
            family=family,
            overfitting_guard=self.overfitting_check.isChecked(),
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
        worker.epoch_metrics.connect(self._on_epoch_metrics)
        worker.abort_reason.connect(self._on_abort_reason)
        worker.finished_training.connect(self._on_finished)
        self.start_button.setEnabled(False)
        self.abort_button.setEnabled(True)
        self.overfitting_check.setEnabled(False)
        self.progress_bar.setRange(0, worker.config.epochs)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Epok %v/%m")
        self.epoch_label.setText("Väntar på första epoken")
        # en ny träning tar över grafen, så ett gammalt val i listan släpps
        self.history.table.clearSelection()
        self.chart.clear()
        self.chart.setVisible(True)
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

    def _on_epoch_metrics(self, metrics) -> None:
        """Uppdaterar progressbaren och grafen med epokens värden (TASK-44, TASK-45)."""
        self.progress_bar.setFormat("Epok %v/%m")
        self.progress_bar.setMaximum(metrics.total_epochs)
        self.progress_bar.setValue(metrics.epoch)
        self.epoch_label.setText(metrics.summary())
        self.chart.add_epoch(metrics)

    def _training_active(self) -> bool:
        return self.worker is not None and self.worker.is_running()

    def _on_history_selected(self, run) -> None:
        """Visar en vald tidigare träning i grafen (TASK-70).

        Under pågående träning visar grafen livedata, så ett val i listan rör
        den inte då. Utan val och utan pågående träning finns inget att visa,
        och då döljs diagramytorna.
        """
        if self._training_active():
            return
        self.chart.clear()
        if run is None:
            self.chart.setVisible(False)
            return
        for metrics in run_epochs(run):
            self.chart.add_epoch(metrics)
        self.chart.setVisible(self.chart.has_data())

    def _on_abort_reason(self, reason: str) -> None:
        """Visar varför träningen avbröts, både i vyn och i statusraden (TASK-46)."""
        self.epoch_label.setText(f"Avbruten: {reason}")
        self.status_changed.emit(f"Träningen avbröts: {reason}")

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
        self.overfitting_check.setEnabled(True)
        self.training_finished.emit()
        self.refresh_dataset_info()
        self.history.refresh()


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
