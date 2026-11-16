"""Lista över tidigare träningar med export och utvärdering av vald modell (TASK-59, TASK-95)."""

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from xray_detector.application.background_task import BackgroundTask
from xray_detector.application.evaluation import (
    SPLIT_LABELS,
    available_splits,
    default_split,
    evaluate_run,
    load_evaluation,
    save_evaluation,
    summary_text,
)
from xray_detector.application.training_history import (
    TrainingRun,
    export_run,
    training_runs,
)
from xray_detector.ui.busy_indicator import BusyIndicator
from xray_detector.ui.shortcuts import mnemonic
from xray_detector.ui.style import button

COLUMNS = ("Körning", "Basmodell", "Epoker", "Tid", "mAP50-95", "Dom", "Status")
NO_RUNS = "Inga tidigare träningar"
NO_SELECTION = "Välj en träning för att exportera modellen"
NOT_EVALUATED = "Inte utvärderad"


class TrainingHistoryView(QWidget):
    """Tabell över models/trained/ med export och utvärdering av vald körning.

    Listan läses från manifesten, så den visar även körningar som gjorts från
    CLI:t. Exporten kopierar vikterna och manifestet till en katalog
    användaren väljer, och utvärderingen sparar sin rapport i körningens
    katalog så två körningar kan jämföras i efterhand.
    """

    #: Vald körning, eller None när inget är valt (TASK-70).
    run_selected = Signal(object)

    def __init__(self, trained_dir: Path, dataset=None, parent=None) -> None:
        super().__init__(parent)
        self.trained_dir = Path(trained_dir)
        self.dataset = dataset
        self.runs: list[TrainingRun] = []
        self.evaluation_report: dict | None = None
        self._evaluate_task: BackgroundTask | None = None
        self._emitted_run_id: str | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(list(COLUMNS))
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table, 1)
        self.details = QLabel(NO_SELECTION)
        self.details.setWordWrap(True)
        layout.addWidget(self.details)
        self.evaluation_label = QLabel(NOT_EVALUATED)
        self.evaluation_label.setWordWrap(True)
        self.evaluation_label.setStyleSheet("color: #888;")
        layout.addWidget(self.evaluation_label)
        buttons = QHBoxLayout()
        self.split_combo = QComboBox()
        self.split_combo.setToolTip(
            "Delmängden modellen utvärderas mot. Test är held-out för RF-DETR; "
            "YOLO-exporten har bara train/val."
        )
        buttons.addWidget(self.split_combo)
        self.evaluate_button = button(mnemonic("Utvärdera...", "U"))
        self.evaluate_button.setEnabled(False)
        self.evaluate_button.clicked.connect(self._on_evaluate)
        buttons.addWidget(self.evaluate_button)
        buttons.addStretch(1)
        self.export_button = button(mnemonic("Exportera modell", "E"))
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self._on_export)
        buttons.addWidget(self.export_button)
        layout.addLayout(buttons)
        self.busy = BusyIndicator(self)
        self._fill_splits("yolo")
        self.refresh()

    def refresh(self) -> None:
        """Läser om manifesten; vald körning behålls när den finns kvar."""
        selected = self.selected_run()
        self.runs = training_runs(self.trained_dir)
        self.table.setRowCount(len(self.runs))
        for row, run in enumerate(self.runs):
            for column, value in enumerate(
                (
                    run.run_id,
                    Path(run.base_weights).stem,
                    run.epochs_text,
                    run.duration_text,
                    run.map50_95_text,
                    run.verdict.label,
                    run.status_label,
                )
            ):
                self.table.setItem(row, column, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()
        if selected is not None:
            self._select(selected.run_id)
        self._on_selection_changed()

    def selected_run(self) -> TrainingRun | None:
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not rows:
            return None
        index = rows[0].row()
        return self.runs[index] if 0 <= index < len(self.runs) else None

    def export_selected(self, target_dir: Path) -> Path | None:
        """Exporterar vald körning; None när inget är valt."""
        run = self.selected_run()
        if run is None:
            return None
        return export_run(run, target_dir)

    def evaluate_selected(self, split: str | None = None) -> dict | None:
        """Utvärderar vald körning och sparar rapporten; None utan val."""
        run = self.selected_run()
        if run is None or self.dataset is None:
            return None
        report = evaluate_run(
            run,
            self.dataset.load_dataset(),
            self.dataset.images_dir,
            split or self.split_combo.currentData(),
        )
        save_evaluation(run, report)
        return report

    def _fill_splits(self, family: str) -> None:
        """Delmängderna som är held-out för familjen, med familjens default vald."""
        current = self.split_combo.currentData()
        self.split_combo.blockSignals(True)
        self.split_combo.clear()
        for split in available_splits(family):
            self.split_combo.addItem(SPLIT_LABELS[split], split)
        index = self.split_combo.findData(current)
        if index < 0:
            index = self.split_combo.findData(default_split(family))
        self.split_combo.setCurrentIndex(max(0, index))
        self.split_combo.blockSignals(False)

    def _select(self, run_id: str) -> None:
        for row, run in enumerate(self.runs):
            if run.run_id == run_id:
                self.table.selectRow(row)
                return

    def _on_selection_changed(self) -> None:
        run = self.selected_run()
        self.export_button.setEnabled(run is not None)
        self.evaluate_button.setEnabled(run is not None and self.dataset is not None)
        self.details.setText(run.details if run is not None else NO_SELECTION)
        self._show_evaluation(run)
        if run is not None:
            self._fill_splits(run.family)
        # Bara ett nytt val sänds vidare; en refresh som behåller valet ska inte
        # släcka grafen som redan visar körningen (TASK-70).
        run_id = run.run_id if run is not None else None
        if run_id != self._emitted_run_id:
            self._emitted_run_id = run_id
            self.run_selected.emit(run)

    def _show_evaluation(self, run: TrainingRun | None) -> None:
        """Visar körningens sparade utvärdering, så två körningar kan jämföras."""
        report = load_evaluation(run) if run is not None else None
        self.evaluation_report = report
        if report is None:
            self.evaluation_label.setText(NOT_EVALUATED if run is not None else "")
            return
        self.evaluation_label.setText(f"Utvärdering ({report.get('split')}): {summary_text(report)}")

    def _on_evaluate(self) -> None:
        run = self.selected_run()
        if run is None or self.dataset is None:
            return
        split = self.split_combo.currentData()
        self.evaluate_button.setEnabled(False)
        self.evaluation_label.setText("Utvärderar...")
        self.busy.start("Utvärderar modellen...")
        task = BackgroundTask(lambda: self.evaluate_selected(split))
        task.succeeded.connect(self._on_evaluated)
        task.failed.connect(self._on_evaluate_failed)
        task.finished.connect(self._on_evaluate_finished)
        self._evaluate_task = task
        task.start()

    def _on_evaluated(self, report) -> None:
        if report is None:
            return
        self.evaluation_report = report
        self.evaluation_label.setText(
            f"Utvärdering ({report.get('split')}): {summary_text(report)}"
        )

    def _on_evaluate_failed(self, message: str) -> None:
        self.evaluation_label.setText(NOT_EVALUATED)
        QMessageBox.warning(self, "Utvärderingen misslyckades", message)

    def _on_evaluate_finished(self) -> None:
        self._evaluate_task = None
        self.busy.stop()
        self.evaluate_button.setEnabled(self.selected_run() is not None)

    def wait_for_evaluation(self, timeout_ms: int = 60000) -> None:
        """Väntar in en pågående utvärdering (tester och stängning)."""
        if self._evaluate_task is not None:
            self._evaluate_task.wait(timeout_ms)

    def _on_export(self) -> None:
        run = self.selected_run()
        if run is None:
            return
        target = QFileDialog.getExistingDirectory(
            self, "Exportera modell", str(Path.home())
        )
        if not target:
            return
        try:
            exported = export_run(run, Path(target))
        except OSError as exc:
            QMessageBox.warning(self, "Exporten misslyckades", str(exc))
            return
        QMessageBox.information(
            self, "Modellen exporterad", f"Vikter och manifest ligger i {exported}"
        )
