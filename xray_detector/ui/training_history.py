"""Lista över tidigare träningar med export av vald modell (TASK-59)."""

from pathlib import Path

from PySide6.QtWidgets import (
    QAbstractItemView,
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

from xray_detector.application.training_history import (
    TrainingRun,
    export_run,
    training_runs,
)
from xray_detector.ui.shortcuts import mnemonic
from xray_detector.ui.style import button

COLUMNS = ("Körning", "Basmodell", "Epoker", "Tid", "mAP50-95", "Status")
NO_RUNS = "Inga tidigare träningar"
NO_SELECTION = "Välj en träning för att exportera modellen"


class TrainingHistoryView(QWidget):
    """Tabell över models/trained/ med export av vald körnings vikter.

    Listan läses från manifesten, så den visar även körningar som gjorts från
    CLI:t. Exporten kopierar vikterna och manifestet till en katalog
    användaren väljer.
    """

    def __init__(self, trained_dir: Path, parent=None) -> None:
        super().__init__(parent)
        self.trained_dir = Path(trained_dir)
        self.runs: list[TrainingRun] = []
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
        buttons = QHBoxLayout()
        self.export_button = button(mnemonic("Exportera modell", "E"))
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self._on_export)
        buttons.addStretch(1)
        buttons.addWidget(self.export_button)
        layout.addLayout(buttons)
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

    def _select(self, run_id: str) -> None:
        for row, run in enumerate(self.runs):
            if run.run_id == run_id:
                self.table.selectRow(row)
                return

    def _on_selection_changed(self) -> None:
        run = self.selected_run()
        self.export_button.setEnabled(run is not None)
        self.details.setText(run.details if run is not None else NO_SELECTION)

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
