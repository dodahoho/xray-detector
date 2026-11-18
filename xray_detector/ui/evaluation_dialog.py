"""Dialog som jämför valda träningar mot en vald källa (TASK-158).

Utvärderingen låg tidigare som en rad under historiktabellen och kunde bara
köra en modell mot en delmängd av datasetet. Här jämförs flera modeller mot
samma källa, och källan kan också vara en mapp med bilder eller en videofil.
De källorna saknar annoteringar, så rapporten räknar detektioner, konfidens
och — för en video — hur stabilt ett spår sitter mellan bildrutorna i stället
för mAP. Rapporten för en datasetkörning sparas i körningens katalog som
tidigare; rapporterna för mapp och video lever bara i dialogen, eftersom de
inte hör till någon delmängd av datasetet.
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from xray_detector.application.background_task import BackgroundTask
from xray_detector.application.evaluation import (
    CONFIDENCE_BINS,
    SOURCE_DATASET,
    SOURCE_FOLDER,
    SOURCE_LABELS,
    SOURCE_VIDEO,
    SPLIT_LABELS,
    EvaluationSource,
    available_splits,
    compare_runs,
    default_split,
    save_evaluation,
)
from xray_detector.ui.busy_indicator import BusyIndicator
from xray_detector.ui.colors import MUTED_TEXT, series_color
from xray_detector.ui.evaluation_chart import BarChart, BarSeries
from xray_detector.ui.shortcuts import mnemonic
from xray_detector.ui.style import button

DATASET_COLUMNS = (
    "Modell",
    "Checkpoint",
    "Bilder",
    "mAP50-95",
    "mAP50",
    "Falsklarm/bild",
    "Tröskel",
    "Recall",
)
DETECTION_COLUMNS = (
    "Modell",
    "Checkpoint",
    "Bilder",
    "Detektioner",
    "Per bild",
    "Med träff",
    "Medelkonfidens",
)
STABILITY_COLUMNS = ("Spår", "Medellängd", "Stabila")
NO_RUNS = "Markera minst en träning i listan."
NO_PATH = "Välj en mapp eller en videofil."
NO_DATASET = "Datasetet är inte tillgängligt."
RUNNING = "Utvärderar modellerna..."
DONE = "Utvärderingen klar: {count} modeller mot {source}."
FAILED = "Utvärderingen misslyckades"
#: Bredden dialogen öppnas med; tabellen och graferna behöver platsen.
DIALOG_WIDTH = 980
DIALOG_HEIGHT = 760
#: Höjden sammanfattningen får; fler modeller än så rullas i tabellen.
TABLE_HEIGHT = 170
#: Lägsta höjden, så rubriken och en rad alltid syns.
MIN_TABLE_HEIGHT = 90


def _percent(value) -> str:
    return f"{float(value or 0.0):.0%}"


def _number(value, decimals: int = 2) -> str:
    return f"{float(value or 0.0):.{decimals}f}"


class EvaluationDialog(QDialog):
    """Jämför valda träningar mot en källa och visar talen och graferna.

    Dialogen äger sin egen utvärdering: den körs i bakgrunden så fönstret
    svarar, och resultatet hamnar i tabellen och i staplarna. Källan väljs
    överst, och en datasetkörning sparas i körningens katalog så historikvyn
    kan visa den efteråt.
    """

    def __init__(
        self,
        runs,
        dataset=None,
        images_dir: Path | None = None,
        parent=None,
        detector_factory=None,
        auto_run: bool = True,
    ) -> None:
        super().__init__(parent)
        self.runs = list(runs)
        self.dataset = dataset
        self.images_dir = images_dir
        self.detector_factory = detector_factory
        self.reports: list[dict] = []
        self._task: BackgroundTask | None = None
        self._runs_by_id = {run.run_id: run for run in self.runs}
        self.setWindowTitle("Utvärdera modeller")
        self.resize(DIALOG_WIDTH, DIALOG_HEIGHT)
        layout = QVBoxLayout(self)
        layout.addWidget(self._build_header())
        layout.addLayout(self._build_source_row())
        self.table = self._build_table()
        layout.addWidget(self.table)
        layout.addWidget(self._build_charts(), 1)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.status.setStyleSheet(f"color: {MUTED_TEXT};")
        layout.addWidget(self.status)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.busy = BusyIndicator(self)
        self._on_source_changed()
        if auto_run:
            self.run_evaluation()

    def _build_header(self) -> QWidget:
        """Raden som säger vilka modeller dialogen jämför."""
        names = ", ".join(run.model_name for run in self.runs) or "-"
        label = QLabel(f"Jämför {len(self.runs)} modeller: {names}")
        label.setWordWrap(True)
        return label

    def _build_source_row(self) -> QHBoxLayout:
        """Källväljaren: dataset med delmängd, bildmapp eller videofil."""
        row = QHBoxLayout()
        self.source_combo = QComboBox()
        for kind in (SOURCE_DATASET, SOURCE_FOLDER, SOURCE_VIDEO):
            self.source_combo.addItem(SOURCE_LABELS[kind], kind)
        self.source_combo.currentIndexChanged.connect(self._on_source_changed)
        row.addWidget(QLabel("Källa:"))
        row.addWidget(self.source_combo)
        self.split_combo = QComboBox()
        self.split_combo.setToolTip(
            "Delmängden modellerna utvärderas mot. Test är held-out för RF-DETR; "
            "YOLO-exporten har bara train/val."
        )
        self._fill_splits()
        row.addWidget(self.split_combo)
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText(NO_PATH)
        row.addWidget(self.path_edit, 1)
        self.browse_button = button(mnemonic("Bläddra...", "B"))
        self.browse_button.clicked.connect(self._on_browse)
        row.addWidget(self.browse_button)
        self.run_button = button(mnemonic("Kör utvärdering", "K"), primary=True)
        self.run_button.clicked.connect(self.run_evaluation)
        row.addWidget(self.run_button)
        return row

    def _build_table(self) -> QTableWidget:
        """Sammanfattningen; kolumnerna beror på källan och sätts när den är körd."""
        table = QTableWidget(0, len(DATASET_COLUMNS))
        table.setHorizontalHeaderLabels(list(DATASET_COLUMNS))
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        # tabellen får höjd efter antalet rader och rullar för resten, så
        # graferna under den behåller höjden även när många modeller jämförs
        table.setFixedHeight(MIN_TABLE_HEIGHT)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        return table

    def _fit_table_height(self) -> None:
        """Ger tabellen höjd efter antalet rader, upp till taket."""
        header = self.table.horizontalHeader().height()
        rows = sum(self.table.rowHeight(row) for row in range(self.table.rowCount()))
        self.table.setFixedHeight(
            min(TABLE_HEIGHT, max(MIN_TABLE_HEIGHT, header + rows + 4))
        )

    def _build_charts(self) -> QWidget:
        """Staplarna; vilka som syns beror på källan."""
        self.map_chart = BarChart("mAP per modell", "mAP")
        self.false_alarm_chart = BarChart("Falsklarm per bild", "Larm/bild")
        self.detection_chart = BarChart("Detektioner per bild", "Detektioner/bild")
        self.confidence_chart = BarChart("Konfidensfördelning", "Detektioner")
        self.stability_chart = BarChart("Andel stabila spår", "Andel", percent=True)
        self.charts = (
            self.map_chart,
            self.false_alarm_chart,
            self.detection_chart,
            self.confidence_chart,
            self.stability_chart,
        )
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        for chart in self.charts:
            chart.setVisible(False)
            layout.addWidget(chart)
        return box

    def _fill_splits(self) -> None:
        """Delmängderna modellerna kan utvärderas mot, med familjens default vald."""
        splits: list[str] = []
        for run in self.runs:
            for split in available_splits(run.family):
                if split not in splits:
                    splits.append(split)
        if not splits:
            splits = ["val", "all"]
        current = self.split_combo.currentData()
        self.split_combo.blockSignals(True)
        self.split_combo.clear()
        for split in splits:
            self.split_combo.addItem(SPLIT_LABELS[split], split)
        index = self.split_combo.findData(current)
        if index < 0:
            index = self.split_combo.findData(default_split(self.runs[0].family))
        self.split_combo.setCurrentIndex(max(0, index))
        self.split_combo.blockSignals(False)

    def _on_source_changed(self, *_args) -> None:
        """Visar bara de fält källan använder och släpper en sökväg som inte passar."""
        kind = self.source_combo.currentData()
        # en mapp duger inte som videofil och tvärtom, så sökvägen nollställs
        if kind != getattr(self, "_kind", kind):
            self.path_edit.clear()
        self._kind = kind
        is_dataset = kind == SOURCE_DATASET
        self.split_combo.setVisible(is_dataset)
        self.path_edit.setVisible(not is_dataset)
        self.browse_button.setVisible(not is_dataset)
        self.path_edit.setPlaceholderText(
            "Välj en mapp med bilder" if kind == SOURCE_FOLDER else "Välj en videofil"
        )
        self.run_button.setEnabled(self._source_ready())

    def _source_ready(self) -> bool:
        """Sant när källan har det som behövs för att kunna köras."""
        if not self.runs:
            return False
        kind = self.source_combo.currentData()
        if kind == SOURCE_DATASET:
            return self.dataset is not None
        return bool(self.path_edit.text())

    def _on_browse(self) -> None:
        """Väljer mapp eller videofil beroende på källan."""
        if self.source_combo.currentData() == SOURCE_FOLDER:
            chosen = QFileDialog.getExistingDirectory(
                self, "Välj en mapp med bilder", str(Path.home())
            )
        else:
            chosen, _filter = QFileDialog.getOpenFileName(
                self,
                "Välj en videofil",
                str(Path.home()),
                "Videofiler (*.mp4 *.avi *.mov *.mkv *.wmv);;Alla filer (*)",
            )
        if chosen:
            self.path_edit.setText(chosen)
            self.run_button.setEnabled(self._source_ready())

    def current_source(self) -> EvaluationSource:
        """Källan fälten beskriver."""
        kind = self.source_combo.currentData()
        if kind == SOURCE_DATASET:
            return EvaluationSource(kind=kind, split=self.split_combo.currentData())
        return EvaluationSource(kind=kind, path=Path(self.path_edit.text()))

    def run_evaluation(self) -> None:
        """Kör jämförelsen i bakgrunden; gör inget när källan inte är komplett."""
        if self._task is not None or not self._source_ready():
            return
        source = self.current_source()
        self.run_button.setEnabled(False)
        self.status.setText(RUNNING)
        self.busy.start(RUNNING)
        task = BackgroundTask(lambda: self._evaluate(source))
        task.succeeded.connect(self._on_evaluated)
        task.failed.connect(self._on_failed)
        task.finished.connect(self._on_finished)
        self._task = task
        task.start()

    def _evaluate(self, source: EvaluationSource) -> list[dict]:
        """Kör jämförelsen och sparar datasetrapporterna i körningarnas kataloger."""
        dataset = self.dataset.load_dataset() if self.dataset is not None else None
        reports = compare_runs(
            self.runs,
            source,
            dataset,
            self.images_dir,
            self.detector_factory,
        )
        if source.kind == SOURCE_DATASET:
            for run, report in zip(self.runs, reports, strict=True):
                save_evaluation(run, report)
        return reports

    def _on_evaluated(self, reports) -> None:
        self.reports = list(reports or [])
        self._fill_table()
        self._fill_charts()
        source = self.current_source().label
        self.status.setText(DONE.format(count=len(self.reports), source=source))

    def _on_failed(self, message: str) -> None:
        self.status.setText("")
        QMessageBox.warning(self, FAILED, message)

    def _on_finished(self) -> None:
        self._task = None
        self.busy.stop()
        self.run_button.setEnabled(self._source_ready())

    def wait_for_evaluation(self, timeout_ms: int = 60000) -> None:
        """Väntar in en pågående utvärdering (tester och stängning)."""
        if self._task is not None:
            self._task.wait(timeout_ms)

    def closeEvent(self, event) -> None:
        self.wait_for_evaluation()
        super().closeEvent(event)

    def _fill_table(self) -> None:
        """Fyller sammanfattningen med de kolumner källan kan svara på."""
        columns = self._columns()
        self.table.clear()
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(list(columns))
        self.table.setRowCount(len(self.reports))
        for row, report in enumerate(self.reports):
            for column, value in enumerate(self._row(report)):
                self.table.setItem(row, column, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._fit_table_height()

    def _columns(self) -> tuple[str, ...]:
        if self._is_dataset():
            return DATASET_COLUMNS
        if self.current_source().temporal:
            return DETECTION_COLUMNS + STABILITY_COLUMNS
        return DETECTION_COLUMNS

    def _is_dataset(self) -> bool:
        return self.current_source().kind == SOURCE_DATASET

    def _run_name(self, report: dict) -> str:
        """Modellens visningsnamn ur rapportens körnings-id."""
        run = self._runs_by_id.get(report.get("run_id"))
        return run.model_name if run is not None else str(report.get("run_id"))

    def _row(self, report: dict) -> list[str]:
        """En rapport som tabellrad, med samma ordning som _columns."""
        run = self._runs_by_id.get(report.get("run_id"))
        checkpoint = Path(run.base_weights).stem if run is not None else "-"
        head = [self._run_name(report), checkpoint, str(report.get("images", 0))]
        if self._is_dataset():
            overall = report.get("overall") or {}
            operating = report.get("operating_point") or {}
            false_alarms = report.get("false_alarms") or {}
            return [
                *head,
                _number(overall.get("map50_95"), 3),
                _number(overall.get("map50"), 3),
                _number(false_alarms.get("per_image")),
                _number(operating.get("threshold")),
                _percent(operating.get("recall")),
            ]
        detections = report.get("detections") or {}
        row = [
            *head,
            str(detections.get("total", 0)),
            _number(detections.get("per_image")),
            _percent(detections.get("with_detection_share")),
            _number(detections.get("mean_confidence")),
        ]
        stability = report.get("stability")
        if self.current_source().temporal:
            stability = stability or {}
            row.extend(
                [
                    str(stability.get("tracks", 0)),
                    _number(stability.get("mean_length"), 1),
                    _percent(stability.get("stable_share")),
                ]
            )
        return row

    def _fill_charts(self) -> None:
        """Visar de grafer källan kan fylla och döljer resten."""
        names = [self._run_name(report) for report in self.reports]
        for chart in self.charts:
            chart.setVisible(False)
        if self._is_dataset():
            self._fill_dataset_charts(names)
            return
        self._fill_detection_charts(names)

    def _fill_dataset_charts(self, names: list[str]) -> None:
        overall = [report.get("overall") or {} for report in self.reports]
        self.map_chart.set_data(
            names,
            [
                BarSeries(
                    "mAP50-95",
                    series_color(0),
                    [float(values.get("map50_95") or 0.0) for values in overall],
                ),
                BarSeries(
                    "mAP50",
                    series_color(1),
                    [float(values.get("map50") or 0.0) for values in overall],
                ),
            ],
        )
        self.false_alarm_chart.set_data(
            names,
            [
                BarSeries(
                    "Falsklarm/bild",
                    series_color(3),
                    [
                        float((report.get("false_alarms") or {}).get("per_image") or 0.0)
                        for report in self.reports
                    ],
                )
            ],
        )
        self.map_chart.setVisible(self.map_chart.has_data())
        self.false_alarm_chart.setVisible(self.false_alarm_chart.has_data())

    def _fill_detection_charts(self, names: list[str]) -> None:
        detections = [report.get("detections") or {} for report in self.reports]
        self.detection_chart.set_data(
            names,
            [
                BarSeries(
                    "Detektioner/bild",
                    series_color(0),
                    [float(values.get("per_image") or 0.0) for values in detections],
                )
            ],
        )
        bins = [
            f"{index / CONFIDENCE_BINS:.1f}-{(index + 1) / CONFIDENCE_BINS:.1f}"
            for index in range(CONFIDENCE_BINS)
        ]
        self.confidence_chart.set_data(
            bins,
            [
                BarSeries(
                    name,
                    series_color(index),
                    [float(value) for value in values.get("histogram") or []],
                )
                for index, (name, values) in enumerate(
                    zip(names, detections, strict=True)
                )
            ],
        )
        self.detection_chart.setVisible(self.detection_chart.has_data())
        self.confidence_chart.setVisible(self.confidence_chart.has_data())
        if not self.current_source().temporal:
            return
        self.stability_chart.set_data(
            names,
            [
                BarSeries(
                    "Stabila spår",
                    series_color(2),
                    [
                        float((report.get("stability") or {}).get("stable_share") or 0.0)
                        for report in self.reports
                    ],
                )
            ],
        )
        self.stability_chart.setVisible(self.stability_chart.has_data())
