"""Graf över loss och mAP per epok i träningsvyn (TASK-45)."""

import ast
import json
from pathlib import Path

import pytest
from PySide6.QtCore import QObject, Signal

from xray_detector.domain.training import EpochMetrics, TrainConfig
from xray_detector.ui.training_chart import (
    EPOCH_AXIS,
    LOSS_AXIS,
    MAP_AXIS,
    MIN_MAP_SPAN,
    TrainingChart,
)


def _points(series) -> list[tuple[float, float]]:
    return [(point.x(), point.y()) for point in series.points()]


def _epoch(epoch: int, **values) -> EpochMetrics:
    return EpochMetrics(epoch=epoch, total_epochs=10, **values)


# --- Serierna får rätt punkter (AC 1, 2, 3, 8) ---


def test_loss_series_get_one_point_per_epoch(qapp):
    chart = TrainingChart()
    chart.add_epoch(_epoch(1, train_loss=2.0, val_loss=2.5))
    chart.add_epoch(_epoch(2, train_loss=1.5, val_loss=2.2))

    assert _points(chart.train_loss) == [(1.0, 2.0), (2.0, 1.5)]
    assert _points(chart.val_loss) == [(1.0, 2.5), (2.0, 2.2)]


def test_map_series_get_one_point_per_epoch(qapp):
    chart = TrainingChart()
    chart.add_epoch(_epoch(1, map50=0.4, map50_95=0.2))
    chart.add_epoch(_epoch(2, map50=0.6, map50_95=0.35))

    assert _points(chart.map50) == [(1.0, 0.4), (2.0, 0.6)]
    assert _points(chart.map50_95) == [(1.0, 0.2), (2.0, 0.35)]


def test_missing_values_are_skipped(qapp):
    chart = TrainingChart()
    chart.add_epoch(_epoch(1, train_loss=2.0))

    assert _points(chart.train_loss) == [(1.0, 2.0)]
    assert _points(chart.val_loss) == []
    assert _points(chart.map50) == []


def test_clear_empties_every_series(qapp):
    chart = TrainingChart()
    chart.add_epoch(_epoch(1, train_loss=2.0, val_loss=2.5, map50=0.4, map50_95=0.2))

    chart.clear()

    for series in (chart.train_loss, chart.val_loss, chart.map50, chart.map50_95):
        assert _points(series) == []


def test_new_epoch_moves_the_axes(qapp):
    chart = TrainingChart()
    chart.add_epoch(_epoch(1, train_loss=2.0, map50=0.4))
    chart.add_epoch(_epoch(5, train_loss=1.0, map50=0.6))

    assert chart.loss_axis_x.min() <= 1.0
    assert chart.loss_axis_x.max() >= 5.0
    assert chart.map_axis_x.max() >= 5.0


# --- Läsbar graf (AC 4, 6) ---


def test_axes_are_labelled(qapp):
    chart = TrainingChart()

    assert chart.loss_axis_x.titleText() == EPOCH_AXIS
    assert chart.map_axis_x.titleText() == EPOCH_AXIS
    assert chart.loss_axis_y.titleText() == LOSS_AXIS
    assert chart.map_axis_y.titleText() == MAP_AXIS
    assert chart.loss_chart.legend().isVisible()
    assert chart.map_chart.legend().isVisible()


def test_single_epoch_gives_a_readable_range(qapp):
    chart = TrainingChart()
    chart.add_epoch(_epoch(1, train_loss=2.0, val_loss=2.0, map50=0.4, map50_95=0.4))

    assert chart.map_axis_y.max() - chart.map_axis_y.min() == pytest.approx(MIN_MAP_SPAN)
    assert chart.loss_axis_y.max() - chart.loss_axis_y.min() > 0
    assert chart.map_axis_x.max() > chart.map_axis_x.min()
    assert chart.map50.pointsVisible()


def test_empty_chart_has_a_usable_range(qapp):
    chart = TrainingChart()

    assert chart.loss_axis_x.max() > chart.loss_axis_x.min()
    assert chart.map_axis_y.max() > chart.map_axis_y.min()


def test_has_data_follows_the_series(qapp):
    chart = TrainingChart()
    assert not chart.has_data()

    chart.add_epoch(_epoch(1, train_loss=2.0))

    assert chart.has_data()

    chart.clear()

    assert not chart.has_data()


# --- Ingen ny dependency (AC 7) ---


def test_chart_module_only_imports_pyside6_and_the_project():
    source = Path("xray_detector/ui/training_chart.py").read_text(encoding="utf-8")
    modules = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])

    assert modules <= {"PySide6", "xray_detector"}


# --- Träningsvyn (AC 3, 5) ---


def _training_view(qapp, tmp_path):
    from PySide6.QtCore import QSettings

    from xray_detector.application.dataset_service import DatasetService
    from xray_detector.domain.config import AppConfig
    from xray_detector.ui.training_view import TrainingView

    config = AppConfig()
    config.data_dir = tmp_path / "data"
    config.models_dir = tmp_path / "models"
    config.ensure_dirs()
    return TrainingView(
        config,
        DatasetService(config.dataset_dir),
        QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat),
    )


def test_training_view_fills_the_chart_from_the_epoch_signal(qapp, tmp_path):
    view = _training_view(qapp, tmp_path)

    view._on_epoch_metrics(_epoch(1, train_loss=2.0, val_loss=2.5, map50=0.4))
    view._on_epoch_metrics(_epoch(2, train_loss=1.5, val_loss=2.2, map50=0.6))

    assert _points(view.chart.train_loss) == [(1.0, 2.0), (2.0, 1.5)]
    assert _points(view.chart.map50) == [(1.0, 0.4), (2.0, 0.6)]


def test_chart_keeps_its_data_after_an_aborted_training(qapp, tmp_path):
    view = _training_view(qapp, tmp_path)
    view._on_epoch_metrics(_epoch(1, train_loss=2.0, map50=0.4))

    view._on_finished(False, "Träning avslutad (kod 1)")

    assert _points(view.chart.train_loss) == [(1.0, 2.0)]
    assert _points(view.chart.map50) == [(1.0, 0.4)]


# --- Diagrammen syns bara när det finns något att visa (TASK-70) ---


class _FakeWorker(QObject):
    """Worker utan process, så vyn kan testas utan att starta en träning."""

    progress = Signal(str)
    epoch_metrics = Signal(object)
    abort_reason = Signal(str)
    finished_training = Signal(bool, str)

    def __init__(self, config: TrainConfig, running: bool = True) -> None:
        super().__init__()
        self.config = config
        self._running = running

    def start(self) -> None:
        pass

    def is_running(self) -> bool:
        return self._running


def _fake_worker(tmp_path, running: bool = True) -> _FakeWorker:
    return _FakeWorker(
        TrainConfig(
            dataset_yaml=tmp_path / "d.yaml",
            weights="yolo26n.pt",
            output_dir=tmp_path / "o",
            epochs=10,
        ),
        running=running,
    )


def _write_run_with_metrics(trained_dir: Path, run_id: str) -> None:
    run_dir = trained_dir / run_id
    weights = run_dir / "yolo" / "weights" / "best.pt"
    weights.parent.mkdir(parents=True, exist_ok=True)
    weights.write_bytes(b"vikter")
    (run_dir / "training_manifest.json").write_text(
        json.dumps(
            {
                "family": "yolo",
                "base_weights": "yolo26n.pt",
                "weights_relative": "yolo/weights/best.pt",
                "epochs": 10,
                "epochs_completed": 2,
                "status": "completed",
                "started": "2026-11-12T09:00:00+00:00",
                "metrics": {"map50_95": 0.35},
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "yolo" / "results.csv").write_text(
        "epoch,train/box_loss,metrics/mAP50-95(B)\n1,2.0,0.2\n2,1.5,0.35\n",
        encoding="utf-8",
    )


def test_chart_is_hidden_before_any_training(qapp, tmp_path):
    view = _training_view(qapp, tmp_path)

    assert view.chart.isHidden()
    assert not view.chart.has_data()


def test_chart_is_shown_when_training_starts(qapp, tmp_path):
    view = _training_view(qapp, tmp_path)

    view._on_worker_created(_fake_worker(tmp_path))

    assert not view.chart.isHidden()


def test_selecting_a_finished_run_shows_its_saved_epochs(qapp, tmp_path):
    view = _training_view(qapp, tmp_path)
    _write_run_with_metrics(view.config.trained_dir, "korning")
    view.history.refresh()

    view.history.table.selectRow(0)

    assert not view.chart.isHidden()
    assert _points(view.chart.train_loss) == [(1.0, 2.0), (2.0, 1.5)]
    assert _points(view.chart.map50_95) == [(1.0, 0.2), (2.0, 0.35)]


def test_clearing_the_selection_hides_the_chart(qapp, tmp_path):
    view = _training_view(qapp, tmp_path)
    _write_run_with_metrics(view.config.trained_dir, "korning")
    view.history.refresh()
    view.history.table.selectRow(0)

    view.history.table.clearSelection()

    assert view.chart.isHidden()
    assert not view.chart.has_data()


def test_selection_does_not_replace_live_data_during_training(qapp, tmp_path):
    view = _training_view(qapp, tmp_path)
    _write_run_with_metrics(view.config.trained_dir, "korning")
    view.history.refresh()
    view._on_worker_created(_fake_worker(tmp_path))
    view._on_epoch_metrics(_epoch(1, train_loss=9.0))

    view.history.table.selectRow(0)

    assert _points(view.chart.train_loss) == [(1.0, 9.0)]


def test_chart_keeps_showing_the_run_after_training_finishes(qapp, tmp_path):
    view = _training_view(qapp, tmp_path)
    view._on_worker_created(_fake_worker(tmp_path))
    view._on_epoch_metrics(_epoch(1, train_loss=2.0))

    view._on_finished(True, "Träning avslutad (kod 0)")

    assert not view.chart.isHidden()
    assert _points(view.chart.train_loss) == [(1.0, 2.0)]


def test_starting_a_training_releases_the_previous_selection(qapp, tmp_path):
    view = _training_view(qapp, tmp_path)
    _write_run_with_metrics(view.config.trained_dir, "korning")
    view.history.refresh()
    view.history.table.selectRow(0)

    view._on_worker_created(_fake_worker(tmp_path))

    assert view.history.selected_run() is None
    assert not view.chart.isHidden()
    assert not view.chart.has_data()
