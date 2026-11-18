"""Lista över tidigare träningar med export och utvärdering av vald modell (TASK-59, TASK-95)."""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
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

from xray_detector.application.evaluation import load_evaluation, summary_text
from xray_detector.application.training_history import (
    TrainingRun,
    delete_run,
    export_run,
    training_runs,
)
from xray_detector.ui.colors import MUTED_TEXT
from xray_detector.ui.evaluation_dialog import EvaluationDialog
from xray_detector.ui.shortcuts import mnemonic
from xray_detector.ui.style import button

#: Kryssrutan för jämförelsen ligger först i varje rad (TASK-158).
CHECK_COLUMN = 0
COLUMNS = (
    "Val",
    "Datum",
    "Modellnamn",
    "Checkpoint",
    "Epoker",
    "Tid",
    "mAP50-95",
    "Status",
    "Notering",
)
NO_SELECTION = "Välj en träning för att exportera modellen"
NOT_EVALUATED = "Inte utvärderad"
NO_CHECKED = "Markera minst en träning för att jämföra modellerna"
DELETE_QUESTION = (
    "Ta bort träningen {run_id}?\n\n"
    "Körningens vikter, manifest, metrics och utvärdering raderas, och modellen "
    "försvinner ur modellväljarna. Det går inte att ångra."
)


def is_active_run(run_dir, active_run_dir) -> bool:
    """Om katalogen är körningen som pågår just nu (TASK-119, TASK-129).

    active_run_dir är en anropbar som ger katalogen träningen skriver i, eller
    None. Den delas av träningshistoriken och modellistan i inställningarna, så
    en pågående träning skyddas på båda ställena.
    """
    active = active_run_dir() if callable(active_run_dir) else active_run_dir
    if active is None or run_dir is None:
        return False
    return Path(run_dir).resolve() == Path(active).resolve()


def confirm_delete_run(parent, run_id: str) -> bool:
    """Frågar innan körningen och dess filer raderas (TASK-119, TASK-129)."""
    answer = QMessageBox.warning(
        parent,
        "Ta bort träningen",
        DELETE_QUESTION.format(run_id=run_id),
        QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
    )
    return answer == QMessageBox.StandardButton.Ok


class TrainingHistoryView(QWidget):
    """Tabell över models/trained/ med export, utvärdering och borttagning.

    Listan läses från manifesten, så den visar även körningar som gjorts från
    CLI:t. Exporten kopierar vikterna och manifestet till en katalog
    användaren väljer, och utvärderingen sparar sin rapport i körningens
    katalog så två körningar kan jämföras i efterhand. Borttagningen raderar
    körningens katalog, så vikter, manifest och metrics försvinner med den.
    """

    #: Vald körning, eller None när inget är valt (TASK-70).
    run_selected = Signal(object)
    #: En körning har tagits bort med sina filer (TASK-119).
    run_deleted = Signal()

    def __init__(
        self, trained_dir: Path, dataset=None, parent=None, active_run_dir=None
    ) -> None:
        super().__init__(parent)
        self.trained_dir = Path(trained_dir)
        self.dataset = dataset
        #: Katalogen för körningen som pågår just nu, så den inte kan tas bort
        self.active_run_dir = active_run_dir or (lambda: None)
        self.runs: list[TrainingRun] = []
        self.evaluation_report: dict | None = None
        #: Jämförelsedialogen, så stängningen kan vänta in en pågående körning
        self.dialog: EvaluationDialog | None = None
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
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.table, 1)
        self.details = QLabel(NO_SELECTION)
        self.details.setWordWrap(True)
        layout.addWidget(self.details)
        self.evaluation_label = QLabel(NOT_EVALUATED)
        self.evaluation_label.setWordWrap(True)
        self.evaluation_label.setStyleSheet(f"color: {MUTED_TEXT};")
        layout.addWidget(self.evaluation_label)
        buttons = QHBoxLayout()
        self.select_all = QCheckBox("Markera alla")
        self.select_all.setToolTip("Markerar alla träningar för jämförelsen")
        self.select_all.stateChanged.connect(self._on_select_all)
        buttons.addWidget(self.select_all)
        self.evaluate_button = button(mnemonic("Utvärdera valda...", "U"))
        self.evaluate_button.setEnabled(False)
        self.evaluate_button.setToolTip(NO_CHECKED)
        self.evaluate_button.clicked.connect(self._on_evaluate)
        buttons.addWidget(self.evaluate_button)
        buttons.addStretch(1)
        self.export_button = button(mnemonic("Exportera modell", "E"))
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self._on_export)
        buttons.addWidget(self.export_button)
        self.delete_button = button(mnemonic("Ta bort träning", "b"))
        self.delete_button.setEnabled(False)
        self.delete_button.setToolTip(
            "Raderar körningens vikter, manifest, metrics och utvärdering, så "
            "modellen försvinner ur modellväljarna"
        )
        self.delete_button.clicked.connect(self._on_delete)
        buttons.addWidget(self.delete_button)
        layout.addLayout(buttons)
        self.refresh()

    def refresh(self) -> None:
        """Läser om manifesten; vald körning och markerade rader behålls."""
        selected = self.selected_run()
        checked = {run.run_id for run in self.checked_runs()}
        self.runs = training_runs(self.trained_dir)
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.runs))
        for row, run in enumerate(self.runs):
            check = QTableWidgetItem()
            check.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            check.setCheckState(
                Qt.CheckState.Checked
                if run.run_id in checked
                else Qt.CheckState.Unchecked
            )
            self.table.setItem(row, CHECK_COLUMN, check)
            for column, value in enumerate(
                (
                    run.started_text,
                    run.model_name,
                    Path(run.base_weights).stem,
                    run.epochs_text,
                    run.duration_text,
                    run.map50_95_text,
                    run.status_label,
                    run.verdict.label,
                ),
                start=CHECK_COLUMN + 1,
            ):
                self.table.setItem(row, column, QTableWidgetItem(value))
        self.table.blockSignals(False)
        self.table.resizeColumnsToContents()
        if selected is not None:
            self._select(selected.run_id)
        self._on_selection_changed()
        self._update_check_state()

    def checked_runs(self) -> list[TrainingRun]:
        """Körningarna vars kryssruta är satt, i listans ordning (TASK-158)."""
        checked = []
        for row, run in enumerate(self.runs):
            item = self.table.item(row, CHECK_COLUMN)
            if item is not None and item.checkState() == Qt.CheckState.Checked:
                checked.append(run)
        return checked

    def _on_item_changed(self, item) -> None:
        """En kryssruta ändrades, så knappen och 'Markera alla' följer med."""
        if item.column() == CHECK_COLUMN:
            self._update_check_state()

    def _update_check_state(self) -> None:
        """Håller 'Markera alla' i takt med raderna och knappen i takt med valet."""
        checked = len(self.checked_runs())
        if not self.runs or checked == 0:
            state = Qt.CheckState.Unchecked
        elif checked == len(self.runs):
            state = Qt.CheckState.Checked
        else:
            state = Qt.CheckState.PartiallyChecked
        self.select_all.blockSignals(True)
        self.select_all.setTristate(state == Qt.CheckState.PartiallyChecked)
        self.select_all.setCheckState(state)
        self.select_all.blockSignals(False)
        self.evaluate_button.setEnabled(checked > 0 and self.dataset is not None)

    def _on_select_all(self, state: int) -> None:
        """Sätter alla rader till samma läge som 'Markera alla'."""
        checked = Qt.CheckState(state) != Qt.CheckState.Unchecked
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            item = self.table.item(row, CHECK_COLUMN)
            if item is not None:
                item.setCheckState(
                    Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
                )
        self.table.blockSignals(False)
        self._update_check_state()

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

    def delete_selected(self) -> bool:
        """Tar bort vald körning med dess filer; False när inget är valt (TASK-119)."""
        run = self.selected_run()
        if not self._delete_enabled(run):
            return False
        delete_run(self.trained_dir, run.run_id)
        self.refresh()
        self.run_deleted.emit()
        return True

    def _delete_enabled(self, run: TrainingRun | None) -> bool:
        """En pågående körning kan inte tas bort medan träningen skriver i den."""
        if run is None:
            return False
        return not is_active_run(run.run_dir, self.active_run_dir)

    def _on_evaluate(self) -> None:
        """Öppnar jämförelsedialogen för de markerade träningarna (TASK-158)."""
        runs = self.checked_runs()
        if not runs or self.dataset is None:
            return
        self.dialog = EvaluationDialog(
            runs,
            self.dataset,
            getattr(self.dataset, "images_dir", None),
            self,
        )
        self.dialog.finished.connect(self._on_dialog_finished)
        self.dialog.open()

    def _on_dialog_finished(self, _result: int) -> None:
        """En ny datasetutvärdering syns i raden under tabellen."""
        self.dialog = None
        self._show_evaluation(self.selected_run())

    def wait_for_evaluation(self, timeout_ms: int = 60000) -> None:
        """Väntar in en pågående utvärdering i dialogen (tester och stängning)."""
        if self.dialog is not None:
            self.dialog.wait_for_evaluation(timeout_ms)

    def _select(self, run_id: str) -> None:
        for row, run in enumerate(self.runs):
            if run.run_id == run_id:
                self.table.selectRow(row)
                return

    def _on_selection_changed(self) -> None:
        run = self.selected_run()
        self.export_button.setEnabled(run is not None)
        self.evaluate_button.setEnabled(run is not None and self.dataset is not None)
        self.delete_button.setEnabled(self._delete_enabled(run))
        self.details.setText(run.details if run is not None else NO_SELECTION)
        self._show_evaluation(run)
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

    def _on_delete(self) -> None:
        """Frågar innan körningen och dess filer raderas (TASK-119)."""
        run = self.selected_run()
        if not self._delete_enabled(run):
            return
        if not confirm_delete_run(self, run.run_id):
            return
        try:
            self.delete_selected()
        except OSError as exc:
            QMessageBox.warning(self, "Borttagningen misslyckades", str(exc))
