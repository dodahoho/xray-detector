"""Dom över hur en träning slutade (TASK-97)."""

import json
from pathlib import Path
from types import SimpleNamespace

from xray_detector.application.training_history import training_runs
from xray_detector.domain.training import EpochMetrics
from xray_detector.infrastructure.training.verdict import (
    IMPROVING,
    OVERFITTING,
    PLATEAUED,
    UNKNOWN,
    verdict,
)


def _args(tmp_path, **overrides):
    """Träningsargumenten som _finish_state läser tidigt stopp ur (TASK-118)."""
    values = {
        "family": "yolo",
        "weights": "yolo26n.pt",
        "output_path": tmp_path,
        "dataset": str(tmp_path / "data.yaml"),
        "epochs": 20,
        "imgsz": 320,
        "batch": 2,
        "device": "cpu",
        "overfitting_guard": "on",
        "overfitting_patience": 2,
        "started": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _epoch(epoch: int, map50_95: float, train_loss: float = 1.0, val_loss: float = 1.0):
    return EpochMetrics(
        epoch=epoch,
        total_epochs=20,
        train_loss=train_loss,
        val_loss=val_loss,
        map50_95=map50_95,
    )


# --- De tre domslagen (AC 1, 4) ---


def test_a_curve_that_is_still_climbing_is_improving():
    epochs = [_epoch(index, 0.10 + 0.02 * index) for index in range(1, 11)]

    result = verdict(epochs)

    assert result.kind == IMPROVING
    assert result.label == "Förbättras"
    assert "Öka antalet epoker" in result.text


def test_a_curve_that_flattens_out_is_plateaued():
    epochs = [_epoch(index, 0.40) for index in range(1, 11)]

    result = verdict(epochs)

    assert result.kind == PLATEAUED
    assert result.label == "Avstannad"
    assert "större modellstorlek" in result.text


def test_a_run_where_train_loss_falls_while_val_loss_rises_is_overfitting():
    epochs = [
        _epoch(index, 0.10 + 0.03 * index, train_loss=2.0 - 0.1 * index, val_loss=1.0)
        for index in range(1, 6)
    ]
    # efter bästa epoken fortsätter train-loss ner medan val-loss vänder upp
    epochs += [
        _epoch(index, 0.20, train_loss=1.5 - 0.1 * index, val_loss=1.0 + 0.2 * index)
        for index in range(6, 11)
    ]

    result = verdict(epochs)

    assert result.kind == OVERFITTING
    assert result.label == "Övertränad"
    assert "mindre modellstorlek" in result.text


def test_a_short_run_cannot_be_judged():
    result = verdict([_epoch(1, 0.2), _epoch(2, 0.3)])

    assert result.kind == UNKNOWN
    assert result.label == "-"


def test_epochs_without_map_are_ignored():
    epochs = [_epoch(index, 0.10 + 0.02 * index) for index in range(1, 11)]
    epochs += [EpochMetrics(epoch=11, total_epochs=20, train_loss=0.5)]

    assert verdict(epochs).kind == IMPROVING


def test_map50_is_used_when_map50_95_is_missing():
    epochs = [
        EpochMetrics(epoch=index, total_epochs=10, map50=0.10 + 0.02 * index)
        for index in range(1, 11)
    ]

    assert verdict(epochs).kind == IMPROVING


# --- Domen i historikvyn (AC 2, 3) ---


def _write_run(
    trained_dir: Path,
    run: str,
    *,
    status: str = "completed",
    stop_reason: str | None = None,
    results: str | None = None,
) -> Path:
    run_dir = trained_dir / run
    weights = run_dir / "yolo" / "weights" / "best.pt"
    weights.parent.mkdir(parents=True, exist_ok=True)
    weights.write_bytes(b"vikter")
    manifest = {
        "family": "yolo",
        "base_weights": "yolo26n.pt",
        "weights_relative": "yolo/weights/best.pt",
        "classes": ["kniv"],
        "dataset_yaml": "C:/data/exports/yolo/data.yaml",
        "epochs": 10,
        "epochs_completed": 10,
        "imgsz": 640,
        "batch": 16,
        "status": status,
        "stop_reason": stop_reason,
        "started": "2026-11-12T09:00:00+00:00",
        "finished": "2026-11-12T09:12:30+00:00",
        "duration_seconds": 750.0,
        "metrics": {"map50_95": 0.412},
    }
    (run_dir / "training_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    if results is not None:
        (run_dir / "yolo" / "results.csv").write_text(results, encoding="utf-8")
    return run_dir


def test_the_verdict_is_computed_from_the_saved_epochs(tmp_path):
    rows = "epoch,train/box_loss,metrics/mAP50-95(B)\n" + "".join(
        f"{index},{2.0 - 0.1 * index},{0.1 + 0.02 * index}\n" for index in range(1, 11)
    )
    _write_run(tmp_path, "korning", results=rows)

    run = training_runs(tmp_path)[0]

    assert run.verdict.kind == IMPROVING
    assert "Notering: fortsätter förbättras" in run.details


def test_a_run_without_saved_epochs_has_no_verdict(tmp_path):
    _write_run(tmp_path, "korning")

    assert training_runs(tmp_path)[0].verdict.kind == UNKNOWN


def test_a_guard_stop_is_distinguishable_from_a_crash(tmp_path):
    _write_run(tmp_path, "overtranad", status="aborted", stop_reason="overfitting")
    _write_run(tmp_path, "kraschad", status="aborted", stop_reason="error")

    runs = {run.run_id: run for run in training_runs(tmp_path)}

    assert runs["overtranad"].status_label == "Avbruten (överträning)"
    assert runs["kraschad"].status_label == "Avbruten (fel)"


def test_the_guard_stop_is_recorded_as_overfitting(tmp_path):
    """Ett tidigt stopp är ett lyckat utfall, inte en krasch (TASK-97, TASK-118)."""
    from xray_detector.infrastructure.training.train_task import (
        _finish_state,
        _RunState,
    )

    state = _RunState(epochs_completed=7)

    _finish_state(_args(tmp_path), state)

    assert (state.status, state.stop_reason) == ("aborted", "overfitting")
    assert state.reason.startswith("Tidigt stopp")


def test_a_crash_keeps_its_error_reason(tmp_path):
    from xray_detector.infrastructure.training.train_task import (
        _finish_state,
        _RunState,
    )

    state = _RunState(status="aborted", reason="CUDA out of memory", stop_reason="error")

    _finish_state(_args(tmp_path), state)

    assert (state.status, state.stop_reason) == ("aborted", "error")


def test_a_run_that_reaches_the_end_is_completed(tmp_path):
    from xray_detector.infrastructure.training.train_task import (
        _finish_state,
        _RunState,
    )

    state = _RunState(epochs_completed=20)

    _finish_state(_args(tmp_path), state)

    assert (state.status, state.stop_reason) == ("completed", None)


def test_an_aborted_run_without_a_reason_keeps_the_plain_label(tmp_path):
    _write_run(tmp_path, "avbruten", status="aborted")

    assert training_runs(tmp_path)[0].status_label == "Avbruten"


def test_the_history_view_shows_the_verdict(qapp, tmp_path):

    from xray_detector.ui.training_history import COLUMNS, TrainingHistoryView

    rows = "epoch,train/box_loss,metrics/mAP50-95(B)\n" + "".join(
        f"{index},{2.0 - 0.1 * index},{0.1 + 0.02 * index}\n" for index in range(1, 11)
    )
    _write_run(tmp_path, "korning", results=rows)

    view = TrainingHistoryView(tmp_path)

    assert "Notering" in COLUMNS
    assert view.table.item(0, COLUMNS.index("Notering")).text() == "Förbättras"
    view.table.selectRow(0)
    assert "Notering: fortsätter förbättras" in view.details.text()
