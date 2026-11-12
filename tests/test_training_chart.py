"""Graf över loss och mAP per epok i träningsvyn (TASK-45)."""

import ast
from pathlib import Path

import pytest

from xray_detector.domain.training import EpochMetrics
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
    config.data_dir = tmp_path
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
