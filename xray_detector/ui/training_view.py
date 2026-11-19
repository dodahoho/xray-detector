import importlib.util
import logging
from datetime import UTC, datetime
from datetime import time as clock_time
from pathlib import Path
from time import time

from PySide6.QtCore import QEvent, QObject, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from xray_detector.application import model_registry
from xray_detector.application.app_config import file_logger, log_path
from xray_detector.application.background_task import BackgroundTask
from xray_detector.application.training_history import run_epochs
from xray_detector.application.training_service import TrainingService
from xray_detector.domain.config import AppConfig
from xray_detector.domain.model_input import DEFAULT_SIZE, MAX_SIZE, MIN_SIZE, STEP
from xray_detector.domain.training import (
    DEFAULT_LEARNING_RATE,
    NIGHT_END_KEY,
    NIGHT_START_KEY,
    TrainConfig,
    default_batch,
    format_clock,
    imgsz_for,
    rfdetr_resolution_error,
    trained_model_name,
)
from xray_detector.infrastructure.dataset_store.export import (
    export_dataset,
    train_val_counts,
)
from xray_detector.infrastructure.dataset_store.store import DatasetStore
from xray_detector.ui.colors import MUTED_TEXT
from xray_detector.ui.model_combo import ModelComboBox
from xray_detector.ui.settings_dialog import (
    TRAIN_RATIO_KEY,
    TrainingScheduleSection,
    settings_button,
    train_ratio,
)
from xray_detector.ui.shortcuts import bind_shortcut, mnemonic, with_hint
from xray_detector.ui.style import FORM_MAX_WIDTH, FormCard, button
from xray_detector.ui.theme_toggle import ThemeToggle
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
    #: Modellistan ändrades, som när en träning togs bort (TASK-119).
    models_changed = Signal()

    def __init__(self, config: AppConfig, dataset: DatasetStore, settings, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.dataset_store = dataset
        self.settings = settings
        self.training_service = TrainingService()
        self.worker = None
        # datasetexporten som körs i bakgrunden vid start (TASK-151)
        self._export_task: BackgroundTask | None = None
        self.training_log = None
        # körningens id, samma sträng i app.log och training.log (TASK-101)
        self.run_id = None
        # bildstorleken följer datasetet tills användaren väljer en egen (TASK-80)
        self._imgsz_user_set = False
        self._applying_imgsz = False
        # batch-defaulten följer modellfamiljen tills användaren väljer en egen (TASK-91)
        self._batch_user_set = False
        self._applying_batch = False
        # senaste förloppseventet inom epoken (TASK-96)
        self._progress_event = None
        self.training_service.worker_created.connect(self._on_worker_created)
        self.training_service.scheduler().status_changed.connect(self.status_changed.emit)
        self._activity_filter = _ActivityFilter(self.training_service.scheduler().record_activity)
        QApplication.instance().installEventFilter(self._activity_filter)
        layout = QVBoxLayout(self)
        layout.addLayout(self._build_header())
        # korten håller sig till vänster, så fälten inte växer över skärmen (TASK-82)
        cards = QHBoxLayout()
        cards.addWidget(self._build_settings())
        cards.addWidget(self._build_dataset_card())
        cards.addStretch(1)
        layout.addLayout(cards)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Ingen träning")
        layout.addWidget(self.progress_bar)
        self.epoch_label = QLabel("Ingen träning pågår")
        layout.addWidget(self.epoch_label)
        # förloppet inom epoken; tomt när ingen träning rapporterar (TASK-96)
        self.epoch_progress_label = QLabel("")
        self.epoch_progress_label.setStyleSheet(f"color: {MUTED_TEXT};")
        layout.addWidget(self.epoch_progress_label)
        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(1000)
        self._progress_timer.timeout.connect(self._refresh_epoch_progress)
        self.chart = TrainingChart()
        # diagramytorna syns bara när det finns något att visa (TASK-70)
        self.chart.setVisible(False)
        layout.addWidget(self.chart, 2)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.history = TrainingHistoryView(
            self.config.trained_dir,
            self.dataset_store,
            active_run_dir=self.active_run_dir,
        )
        self.history.run_selected.connect(self._on_history_selected)
        # en borttagen träning försvinner ur modellväljarna (TASK-119)
        self.history.run_deleted.connect(self._on_run_deleted)
        self.bottom_tabs = QTabWidget()
        self.bottom_tabs.addTab(self.log, "Logg")
        self.bottom_tabs.addTab(self.history, "Tidigare träningar")
        layout.addWidget(self.bottom_tabs, 1)
        self.refresh_dataset_info()

    def refresh_models(self) -> None:
        """Bygger om basmodellistan och behåller valet (TASK-81, TASK-130).

        Egentränade modeller är också valbara, så en tidigare träning kan
        vidaretränas från sina bästa vikter.
        """
        self.model_combo.fill(
            model_registry.available_models(
                self.config.models_dir, self.config.trained_dir
            ),
            self.model_combo.currentData(),
        )
        self._specs = self.model_combo.specs

    def _build_header(self) -> QHBoxLayout:
        """Inställningsknappen högst upp till höger, som i de andra vyerna."""
        header = QHBoxLayout()
        header.addStretch(1)
        self.settings_button = settings_button(
            self, "Inställningar – Träning", self._settings_sections
        )
        header.addWidget(self.settings_button)
        self.theme_toggle = ThemeToggle(self.settings)
        header.addWidget(self.theme_toggle)
        return header

    def _settings_sections(self) -> list:
        """Träningsschemat; andelen train/val ställs in i Dataset-kortet (TASK-7, TASK-103)."""
        return [TrainingScheduleSection(self.settings)]

    def _build_settings(self) -> FormCard:
        """Träningsinställningarna i ett kort med maxbredd (TASK-82)."""
        card = FormCard("Träningsinställningar")
        form = card.form
        self.model_combo = ModelComboBox()
        self.refresh_models()
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)
        form.addRow("Basmodell:", self.model_combo)
        self.epochs_spin = QSpinBox()
        self.epochs_spin.setRange(1, 1000)
        self.epochs_spin.setValue(100)
        form.addRow("Epoker:", self.epochs_spin)
        self.imgsz_spin = QSpinBox()
        self.imgsz_spin.setRange(MIN_SIZE, MAX_SIZE)
        self.imgsz_spin.setSingleStep(STEP)
        self.imgsz_spin.setValue(DEFAULT_SIZE)
        self.imgsz_spin.valueChanged.connect(self._on_imgsz_changed)
        # värdet är en kvadrat, så den längsta sidan måste rymmas (TASK-87)
        self.imgsz_spin.setToolTip(
            "Bildens längsta sida i pixlar. Ultralytics skalar bilden till en "
            "kvadrat på Bildstorlek x Bildstorlek px: 1280x720 ger 1280 "
            "(horisontell) och 720x1280 ger 1280 (vertikal)."
        )
        form.addRow("Bildstorlek (längsta sidan):", self.imgsz_spin)
        # upplösningarna får en egen rad, annars klipps listan i ett smalt kort
        self.imgsz_info = QLabel("-")
        self.imgsz_info.setStyleSheet(f"color: {MUTED_TEXT};")
        self.imgsz_info.setWordWrap(True)
        form.addRow(self.imgsz_info)
        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 128)
        self.batch_spin.setValue(default_batch(self._family()))
        self.batch_spin.valueChanged.connect(self._on_batch_changed)
        self.batch_spin.setToolTip(
            "Bilder per steg. RF-DETR large får slut på minne på ett 16 GB-kort "
            "med batch 16 vid bildstorlek 704, så RF-DETR utgår från 4."
        )
        form.addRow("Batch:", self.batch_spin)
        self.lr_spin = QDoubleSpinBox()
        self.lr_spin.setDecimals(6)
        self.lr_spin.setRange(0.000001, 0.01)
        self.lr_spin.setSingleStep(0.00001)
        self.lr_spin.setValue(DEFAULT_LEARNING_RATE)
        self.lr_spin.setToolTip(
            "Inlärningshastighet (learning rate). Ett dataset under 1000 samples "
            "överanpassas snabbt, så default är 0.00005 (5e-5)."
        )
        form.addRow("Inlärningshastighet:", self.lr_spin)
        self.run_combo = QComboBox()
        self.run_combo.addItem("Direkt", "direct")
        self.run_combo.addItem("Nattetid (schema)", "night")
        self.run_combo.addItem("Efter inaktivitet", "inactivity")
        self.run_combo.currentIndexChanged.connect(self._update_start_label)
        form.addRow("Kör:", self.run_combo)
        self.overfitting_check = QCheckBox("Avbryt vid överträning")
        self.overfitting_check.setChecked(True)
        self.overfitting_check.setToolTip(
            "Stoppar träningen med ramverkets early stopping när valvärdet inte "
            "förbättrats under tio epoker"
        )
        form.addRow("Överträning:", self.overfitting_check)
        self.start_button = button(mnemonic("Starta träning", "R"), primary=True)
        self.start_button.clicked.connect(self._on_start)
        self._update_start_label()
        self.abort_button = button(with_hint("Avbryt", "Esc"))
        self.abort_button.setEnabled(False)
        self.abort_button.clicked.connect(self._on_abort)
        buttons = QHBoxLayout()
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.abort_button)
        form.addRow(buttons)
        bind_shortcut(self, "Esc", self._on_abort)
        return card

    def _build_dataset_card(self) -> FormCard:
        """Datasetet träningen utgår från, med andelen train/val (TASK-103).

        Kortet står till höger om träningsinställningarna, så storleken på
        datasetet och delningen syns utan att öppna inställningsdialogen.
        """
        card = FormCard("Dataset")
        # kortet delar bredd med träningsinställningarna, så raden blir jämn
        card.setMinimumWidth(FORM_MAX_WIDTH)
        form = card.form
        self.dataset_info = QLabel("-")
        # sammanställningen kan bli lång; den radbryts i stället för att klippas
        self.dataset_info.setWordWrap(True)
        form.addRow(self.dataset_info)
        self.ratio_spin = QSpinBox()
        self.ratio_spin.setRange(1, 99)
        self.ratio_spin.setSuffix(" %")
        self.ratio_spin.setValue(round(train_ratio(self.settings) * 100))
        self.ratio_spin.valueChanged.connect(self._on_ratio_changed)
        form.addRow("Andel till train:", self.ratio_spin)
        hint = QLabel("Resten används till validering. Delningen sker per bildpar.")
        hint.setStyleSheet(f"color: {MUTED_TEXT};")
        hint.setWordWrap(True)
        form.addRow(hint)
        return card

    def _on_ratio_changed(self, percent: int) -> None:
        """Andelen sparas direkt och redovisningen räknas om (TASK-103)."""
        self.settings.setValue(TRAIN_RATIO_KEY, percent)
        self.refresh_dataset_info()

    def _update_start_label(self, *_args) -> None:
        """Knappen säger Schemalägg när jobbet köas i stället för att starta direkt (TASK-104).

        Mnemoniken följer etiketten, så Alt+R och Alt+S pekar ut samma knapp i
        det läge den står i.
        """
        if self.run_combo.currentData() == "direct":
            self.start_button.setText(mnemonic("Starta träning", "R"))
        else:
            self.start_button.setText(mnemonic("Schemalägg träning", "S"))

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

    def _family(self) -> str:
        """Vald basmodells familj; yolo när inget är valt."""
        spec = self._specs.get(self.model_combo.currentData())
        return spec.family if spec is not None else "yolo"

    def _on_model_changed(self) -> None:
        """Batch-defaulten följer familjen tills användaren väljer ett eget värde (TASK-91)."""
        if not self._batch_user_set:
            self._set_batch(default_batch(self._family()), user=False)
        self.refresh_dataset_info()

    def _on_batch_changed(self, _value: int) -> None:
        if not self._applying_batch:
            self._batch_user_set = True

    def _set_batch(self, value: int, user: bool) -> None:
        """Sätter batchen utan att den räknas som ett användarval."""
        self._applying_batch = True
        self.batch_spin.setValue(value)
        self._applying_batch = False
        self._batch_user_set = user

    def restore_settings(self) -> None:
        self._migrate_night_window()
        saved = self.settings.value("training/base_model", type=str)
        if saved:
            index = self.model_combo.findData(saved)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
        value = self.settings.value("training/epochs", 100, type=int)
        if value:
            self.epochs_spin.setValue(value)
        # utan sparat val fortsätter batch att följa modellfamiljen (TASK-91)
        saved_batch = self.settings.value("training/batch", type=int)
        if saved_batch:
            self._set_batch(saved_batch, user=True)
        # inlärningshastigheten följer varken familj eller dataset, så den sparas alltid (TASK-162)
        self.lr_spin.setValue(
            self.settings.value(
                "training/learning_rate", DEFAULT_LEARNING_RATE, type=float
            )
        )
        # utan sparat val fortsätter storleken att följa datasetet (TASK-80)
        saved_imgsz = self.settings.value("training/imgsz", type=int)
        if saved_imgsz:
            self._set_imgsz(saved_imgsz, user=True)
        self.overfitting_check.setChecked(
            self.settings.value("training/overfitting_guard", True, type=bool)
        )

    def _migrate_night_window(self) -> None:
        """Flyttar de gamla _hour-nycklarna till nattfönstrets "HH:MM"-nycklar (TASK-125).

        Dialogen sparade timmen i en egen int-nyckel och tiden som "HH:00" i en
        annan, så samma värde kunde glida isär. Nu finns bara "HH:MM"-nyckeln;
        en sparad timme skrivs om en gång och den gamla nyckeln tas bort.
        """
        for key in (NIGHT_START_KEY, NIGHT_END_KEY):
            hour_key = f"{key}_hour"
            hour = self.settings.value(hour_key, type=int)
            if hour is None:
                continue
            if not self.settings.contains(key):
                self.settings.setValue(key, format_clock(clock_time(hour % 24, 0)))
            self.settings.remove(hour_key)

    def save_settings(self) -> None:
        self.settings.setValue("training/base_model", self.model_combo.currentData())
        self.settings.setValue("training/epochs", self.epochs_spin.value())
        if self._imgsz_user_set:
            self.settings.setValue("training/imgsz", self.imgsz_spin.value())
        if self._batch_user_set:
            self.settings.setValue("training/batch", self.batch_spin.value())
        self.settings.setValue("training/learning_rate", self.lr_spin.value())
        self.settings.setValue(
            "training/overfitting_guard", self.overfitting_check.isChecked()
        )

    def refresh_dataset_info(self) -> None:
        """Visar sammanställningen för datasetet som träningen utgår från.

        Train/val räknas i bildpar, eftersom delningen sker per fångstgrupp (TASK-72).
        Bildstorlekens default följer datasetets vanligaste upplösning (TASK-80).
        """
        info = self.dataset_store.metadata()
        num_train, num_val = train_val_counts(
            self.dataset_store, train_ratio(self.settings), family=self._family()
        )
        self.dataset_info.setText(
            f"Bilder: {info['num_images']}  Objekt: {info['num_objects']}  "
            f"Train/val: {num_train}/{num_val} par  "
            f"Uppdaterad: {info['updated'][:10]}"
        )
        sizes = self.dataset_store.image_sizes()
        self.imgsz_info.setText(_format_image_sizes(sizes))
        if sizes and not self._imgsz_user_set:
            self._set_imgsz(imgsz_for(sizes[0][0], sizes[0][1]), user=False)

    def _trained_name(self, spec, now: datetime) -> str:
        """Visningsnamn för körningen enligt TASK-108:s mönster.

        Basmodellens namn ärvs när basen är en egen tränad modell, så en
        vidareträning på samma dataset bara byter datum.
        """
        pairs, synthetic = self.dataset_store.dataset_counts()
        return trained_model_name(
            base_name=spec.base_name or spec.label,
            date=now.strftime("%Y-%m-%d"),
            pairs=pairs,
            synthetic=synthetic,
            classes=len(self.dataset_store.classes()),
        )

    def _on_start(self) -> None:
        if self.dataset_store.metadata()["num_images"] == 0:
            self.status_changed.emit("Datasetet är tomt")
            return
        spec = self._specs.get(self.model_combo.currentData())
        if spec is None:
            self.status_changed.emit("Ingen basmodell vald")
            return
        family = spec.family
        ratio = train_ratio(self.settings)
        if family == "rfdetr":
            if importlib.util.find_spec("rfdetr") is None:
                self.status_changed.emit(
                    "RF-DETR kraver rfdetr-paketet (uv sync --extra rfdetr)"
                )
                return
            # en upplösning RF-DETR inte kan använda avvisas innan processen
            # startar, så felet syns direkt i stället för i träningsloggen (TASK-91)
            error = rfdetr_resolution_error(self.imgsz_spin.value())
            if error is not None:
                self.status_changed.emit(error)
                return

        def export() -> Path:
            """Exporterar datasetet för körningen; körs när träningen startar (TASK-151)."""
            return export_dataset(
                self.dataset_store, self.config.export_dir, family, ratio
            )

        now = datetime.now(UTC)
        config = TrainConfig(
            weights=spec.weights,
            output_dir=self.config.trained_dir / now.strftime("%Y-%m-%d_%H%M%S"),
            epochs=self.epochs_spin.value(),
            imgsz=self.imgsz_spin.value(),
            batch=self.batch_spin.value(),
            learning_rate=self.lr_spin.value(),
            family=family,
            overfitting_guard=self.overfitting_check.isChecked(),
            name=self._trained_name(spec, now),
            base_name=spec.base_name or spec.label,
        )
        run_mode = self.run_combo.currentData()
        if run_mode == "direct":
            self._start_direct(config, export)
            return
        scheduler = self.training_service.scheduler()
        scheduler.queue_job(
            config,
            run_mode,
            export=export,
            inactivity_minutes=int(self.settings.value("training/inactivity_minutes", 30, type=int)),
            night_start=str(self.settings.value(NIGHT_START_KEY, "")),
            night_end=str(self.settings.value(NIGHT_END_KEY, "")),
        )

    def _start_direct(self, config: TrainConfig, export) -> None:
        """Exporterar datasetet i bakgrunden och startar sedan träningen (TASK-151).

        Exporten låg tidigare i GUI-tråden och frös vyn medan katalogen tömdes
        och alla bilder kopierades.
        """
        if self._export_task is not None:
            return
        self.status_changed.emit("Exporterar datasetet...")
        task = BackgroundTask(export)
        task.succeeded.connect(lambda path: self._on_exported(config, path))
        task.failed.connect(
            lambda message: self.status_changed.emit(
                f"Kunde inte exportera datasetet: {message}"
            )
        )
        task.finished.connect(self._on_export_finished)
        self._export_task = task
        task.start()

    def _on_exported(self, config: TrainConfig, path) -> None:
        config.dataset_yaml = Path(path)
        self.training_service.create_worker(config)

    def _on_export_finished(self) -> None:
        self._export_task = None

    def wait_for_export(self, timeout_ms: int = 10000) -> None:
        """Väntar in en pågående datasetexport (tester och stängning)."""
        if self._export_task is not None:
            self._export_task.wait(timeout_ms)

    def _on_worker_created(self, worker) -> None:
        """Kopplar en (direkt eller schemalagd) worker till loggen och startar den."""
        self.worker = worker
        # körningskatalogen är tidsstämplad och unik per träning (TASK-101)
        self.run_id = worker.config.output_dir.name
        self.training_log = file_logger(
            "xray.training", log_path(self.config.logs_dir, "training")
        )
        worker.progress.connect(self._on_progress)
        worker.epoch_metrics.connect(self._on_epoch_metrics)
        worker.progress_event.connect(self._on_progress_event)
        worker.abort_reason.connect(self._on_abort_reason)
        worker.finished_training.connect(self._on_finished)
        self.start_button.setEnabled(False)
        self.abort_button.setEnabled(True)
        self.overfitting_check.setEnabled(False)
        self.progress_bar.setRange(0, worker.config.epochs)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Epok %v/%m")
        self.epoch_label.setText("Väntar på första epoken")
        self._clear_epoch_progress()
        self._progress_timer.start()
        # en ny träning tar över grafen, så ett gammalt val i listan släpps
        self.history.table.clearSelection()
        # jämförelsen väntar medan träningen har GPU:n (TASK-158)
        self.history.set_training_active(True)
        self.chart.clear()
        self.chart.setVisible(True)
        header = (
            f"[{self.run_id}] Startar träning: {worker.config.weights} på "
            f"{worker.config.dataset_yaml} "
            f"({worker.config.epochs} epoker, imgsz {worker.config.imgsz}, "
            f"batch {worker.config.batch_size()}, "
            f"lr {worker.config.learning_rate:g}) "
            f"-> {worker.config.output_dir}"
        )
        self.log.appendPlainText(header)
        self.training_log.info("=== %s ===", header)
        logging.getLogger("xray").info(
            "Träning %s startad: %s på %s -> %s",
            self.run_id,
            worker.config.weights,
            worker.config.dataset_yaml,
            worker.config.output_dir,
        )
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

    def _on_progress_event(self, event) -> None:
        """Visar hur långt epoken kommit medan den pågår (TASK-96)."""
        self._progress_event = event
        self._refresh_epoch_progress()

    def _refresh_epoch_progress(self) -> None:
        """Ritar om epokförloppet och markerar en gammal heartbeat som inaktuell.

        Träningsprocessen skriver en förloppsrad varannat sekund. Kommer ingen
        ny rad på en stund är det som visas inte längre sant, och då säger vyn
        det i stället för att låta siffran se aktuell ut.
        """
        event = self._progress_event
        if event is None:
            return
        now = time()
        if event.is_stale(now):
            self.epoch_progress_label.setText(
                f"{event.summary()} · ingen rapport på {round(event.age(now))} s"
            )
            return
        self.epoch_progress_label.setText(event.summary())

    def _clear_epoch_progress(self) -> None:
        """Tar bort epokförloppet, så inget ser ut att pågå efter ett avbrott."""
        self._progress_event = None
        self._progress_timer.stop()
        self.epoch_progress_label.clear()

    def _training_active(self) -> bool:
        return self.worker is not None and self.worker.is_running()

    def active_run_dir(self) -> Path | None:
        """Katalogen träningen skriver i just nu, så historiken inte tar bort den (TASK-119)."""
        if not self._training_active():
            return None
        return Path(self.worker.config.output_dir)

    def _on_run_deleted(self) -> None:
        """En borttagen träning försvinner ur modellväljarna (TASK-119)."""
        self.status_changed.emit("Träningen borttagen – modellväljarna uppdaterade")
        self.models_changed.emit()

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
        self._clear_epoch_progress()
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
        logging.getLogger("xray").info("Träning %s avslutad: %s", self.run_id, message)
        self.start_button.setEnabled(True)
        self.abort_button.setEnabled(False)
        self.overfitting_check.setEnabled(True)
        # ett avslutat lopp får inte lämna kvar ett förlopp som ser pågående ut
        self._clear_epoch_progress()
        self.training_finished.emit()
        self.refresh_dataset_info()
        self.history.set_training_active(False)
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
