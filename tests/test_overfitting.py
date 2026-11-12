"""Överträningsdetektion som avbryter träningen (TASK-46)."""

import json
import time
from types import SimpleNamespace

from xray_detector.domain.training import EpochMetrics, TrainConfig
from xray_detector.infrastructure.training.epoch_metrics import (
    ABORT_MARKER,
    abort_line,
    parse_abort_line,
)
from xray_detector.infrastructure.training.overfitting import OverfittingGuard


def _epoch(epoch: int, train_loss: float, map50_95: float | None) -> EpochMetrics:
    return EpochMetrics(
        epoch=epoch,
        total_epochs=20,
        train_loss=train_loss,
        map50_95=map50_95,
    )


# --- Syntetiska kurvor (AC 10) ---


def test_guard_fires_when_train_loss_falls_and_val_map_turns_down():
    """Klassisk överträning: train-loss ner, val-mAP stilla eller ner."""
    guard = OverfittingGuard(patience=3)
    curve = [
        _epoch(1, 3.0, 0.10),
        _epoch(2, 2.5, 0.30),
        _epoch(3, 2.0, 0.31),
        _epoch(4, 1.5, 0.30),
        _epoch(5, 1.0, 0.29),
        _epoch(6, 0.6, 0.28),
    ]

    reasons = [guard.update(metrics) for metrics in curve]

    assert reasons[:5] == [None] * 5
    assert reasons[5] is not None
    assert "Överträning" in reasons[5]
    assert "epok 3" in reasons[5]


def test_guard_stays_quiet_while_val_map_improves():
    guard = OverfittingGuard(patience=3)
    curve = [_epoch(epoch, 3.0 - epoch * 0.2, 0.1 + epoch * 0.05) for epoch in range(1, 10)]

    assert [guard.update(metrics) for metrics in curve] == [None] * 9


def test_guard_stays_quiet_when_train_loss_also_stalls():
    """Avstannad utveckling är inte överträning."""
    guard = OverfittingGuard(patience=2)
    curve = [_epoch(epoch, 2.0, 0.3) for epoch in range(1, 8)]

    assert [guard.update(metrics) for metrics in curve] == [None] * 7


def test_guard_waits_for_patience():
    guard = OverfittingGuard(patience=5)
    curve = [_epoch(epoch, 3.0 - epoch * 0.2, 0.3) for epoch in range(1, 6)]

    assert [guard.update(metrics) for metrics in curve] == [None] * 5


def test_guard_falls_back_to_val_loss_without_map():
    guard = OverfittingGuard(patience=2)
    curve = [
        EpochMetrics(epoch=1, total_epochs=10, train_loss=3.0, val_loss=1.0),
        EpochMetrics(epoch=2, total_epochs=10, train_loss=2.5, val_loss=1.1),
        EpochMetrics(epoch=3, total_epochs=10, train_loss=2.0, val_loss=1.2),
        EpochMetrics(epoch=4, total_epochs=10, train_loss=1.5, val_loss=1.3),
    ]

    reasons = [guard.update(metrics) for metrics in curve]

    assert reasons[2] is not None


def test_guard_ignores_epochs_without_validation_values():
    guard = OverfittingGuard(patience=1)

    assert guard.update(EpochMetrics(epoch=1, total_epochs=5, train_loss=2.0)) is None


def test_guard_reports_the_same_reason_once():
    guard = OverfittingGuard(patience=1)
    guard.update(_epoch(1, 3.0, 0.3))
    first = guard.update(_epoch(2, 2.0, 0.3))

    assert first is not None
    assert guard.update(_epoch(3, 1.0, 0.3)) == first


# --- Avbrottet sker i träningsprocessen (AC 4, 5) ---


def test_apply_stop_stops_the_yolo_trainer():
    from xray_detector.infrastructure.training.train_task import (
        _apply_stop,
        _StopSignal,
    )

    trainer = SimpleNamespace(stop=False)
    _apply_stop(trainer, _StopSignal())
    assert trainer.stop is False

    _apply_stop(trainer, _StopSignal(reason="Överträning"))
    assert trainer.stop is True


def _args(tmp_path, **overrides):
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


def _wait_for(predicate, timeout_s=5.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_reporter_aborts_training_when_overfitting_is_detected(tmp_path, capsys):
    from xray_detector.infrastructure.training.train_task import (
        _RunState,
        _start_reporter,
        _StopSignal,
    )

    args = _args(tmp_path)
    run_dir = tmp_path
    metrics_path = run_dir / "yolo" / "results.csv"
    metrics_path.parent.mkdir(parents=True)
    metrics_path.write_text(
        "epoch,train/box_loss,metrics/mAP50-95(B)\n", encoding="utf-8"
    )
    state = _RunState()
    stop = _StopSignal()
    reporter = _start_reporter(args, run_dir, state, stop)
    try:
        with open(metrics_path, "a", encoding="utf-8") as file:
            file.write("1,3.0,0.3\n")
            file.write("2,2.5,0.3\n")
            file.write("3,2.0,0.3\n")
        assert _wait_for(lambda: stop.reason is not None)
    finally:
        reporter.stop()
        reporter.join(timeout=5)

    assert "Överträning" in stop.reason
    assert any(
        line.startswith(ABORT_MARKER) for line in capsys.readouterr().out.splitlines()
    )


def test_reporter_does_not_abort_when_the_guard_is_off(tmp_path):
    from xray_detector.infrastructure.training.train_task import (
        _RunState,
        _start_reporter,
        _StopSignal,
    )

    args = _args(tmp_path, overfitting_guard="off")
    metrics_path = tmp_path / "yolo" / "results.csv"
    metrics_path.parent.mkdir(parents=True)
    metrics_path.write_text(
        "epoch,train/box_loss,metrics/mAP50-95(B)\n", encoding="utf-8"
    )
    stop = _StopSignal()
    reporter = _start_reporter(args, tmp_path, _RunState(), stop)
    try:
        with open(metrics_path, "a", encoding="utf-8") as file:
            file.writelines(f"{epoch},{3.0 - epoch * 0.2},0.3\n" for epoch in range(1, 8))
        time.sleep(0.3)
    finally:
        reporter.stop()
        reporter.join(timeout=5)

    assert stop.reason is None


def test_manifest_records_the_abort_reason(tmp_path):
    from xray_detector.infrastructure.training.train_task import (
        _RunState,
        _write_manifest,
    )

    run_dir = tmp_path / "korning"
    weights = run_dir / "yolo" / "weights" / "best.pt"
    weights.parent.mkdir(parents=True)
    weights.write_bytes(b"vikter")
    state = _RunState(status="aborted", reason="Överträning", epochs_completed=7)

    _write_manifest(_args(run_dir), run_dir, state)

    manifest = json.loads((run_dir / "training_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "aborted"
    assert manifest["abort_reason"] == "Överträning"
    assert manifest["epochs_completed"] == 7


def test_rfdetr_gets_early_stopping_when_the_guard_is_on(monkeypatch, tmp_path):
    import sys
    import types

    captured = {}

    class _FakeNano:
        def train(self, **kwargs):
            captured.update(kwargs)

    fake = types.ModuleType("rfdetr")
    fake.RFDETRNano = _FakeNano
    monkeypatch.setitem(sys.modules, "rfdetr", fake)

    from xray_detector.infrastructure.training.train_task import _train_rfdetr

    _train_rfdetr(_args(tmp_path, family="rfdetr", weights="rfdetr-nano"), "cpu")

    assert captured["early_stopping"] is True
    assert captured["early_stopping_patience"] == 2


def test_rfdetr_gets_no_early_stopping_when_the_guard_is_off(monkeypatch, tmp_path):
    import sys
    import types

    captured = {}

    class _FakeNano:
        def train(self, **kwargs):
            captured.update(kwargs)

    fake = types.ModuleType("rfdetr")
    fake.RFDETRNano = _FakeNano
    monkeypatch.setitem(sys.modules, "rfdetr", fake)

    from xray_detector.infrastructure.training.train_task import _train_rfdetr

    _train_rfdetr(
        _args(tmp_path, family="rfdetr", weights="rfdetr-nano", overfitting_guard="off"),
        "cpu",
    )

    assert "early_stopping" not in captured


# --- GUI:t (AC 1, 2, 3, 6, 9) ---


def _training_view(qapp, tmp_path, settings=None):
    from PySide6.QtCore import QSettings

    from xray_detector.application.dataset_service import DatasetService
    from xray_detector.domain.config import AppConfig
    from xray_detector.ui.training_view import TrainingView

    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    if settings is None:
        settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    return TrainingView(config, DatasetService(config.dataset_dir), settings)


def test_setting_is_on_by_default(qapp, tmp_path):
    view = _training_view(qapp, tmp_path)

    assert view.overfitting_check.isChecked()
    assert view.overfitting_check.text() == "Avbryt vid överträning"


def test_setting_is_saved_and_restored(qapp, tmp_path):
    from PySide6.QtCore import QSettings

    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    view = _training_view(qapp, tmp_path, settings)
    view.overfitting_check.setChecked(False)
    view.save_settings()
    settings.sync()

    restored = _training_view(qapp, tmp_path, settings)
    restored.restore_settings()

    assert restored.overfitting_check.isChecked() is False


def test_setting_is_passed_to_the_training_process(qapp, tmp_path):
    import numpy as np

    from xray_detector.domain.dataset import AnnotatedImage

    view = _training_view(qapp, tmp_path)
    view.dataset_service.add_samples(
        [AnnotatedImage(np.zeros((20, 30, 3), np.uint8),
                        [{"class_name": "kniv", "bbox": [1, 1, 4, 4]}])]
    )
    view.refresh_dataset_info()
    started = []
    view.training_service.create_worker = lambda cfg: started.append(cfg)
    view.model_combo.setCurrentIndex(view.model_combo.findData("yolo26n"))
    view.run_combo.setCurrentIndex(view.run_combo.findData("direct"))

    view.overfitting_check.setChecked(False)
    view._on_start()

    assert started[0].overfitting_guard is False
    from xray_detector.infrastructure.training.trainer import TrainingWorker

    command = TrainingWorker(started[0]).command()
    assert command[command.index("--overfitting-guard") + 1] == "off"


def test_view_shows_why_the_training_was_aborted(qapp, tmp_path):
    view = _training_view(qapp, tmp_path)
    messages = []
    view.status_changed.connect(messages.append)

    view._on_abort_reason("Överträning: valvärdet har inte förbättrats sedan epok 2")

    assert view.epoch_label.text().startswith("Avbruten:")
    assert "epok 2" in view.epoch_label.text()
    assert messages and "Överträning" in messages[0]


def test_worker_emits_the_abort_reason(qapp, tmp_path):
    import sys

    from xray_detector.infrastructure.training.trainer import TrainingWorker

    reason = "Överträning: valvärdet har inte förbättrats sedan epok 2"
    script = (
        "import sys\n"
        f"sys.stdout.write({abort_line(reason)!r} + '\\n')\n"
        "sys.stdout.flush()\n"
    )
    config = TrainConfig(
        dataset_yaml=tmp_path / "d.yaml",
        weights="yolo26n.pt",
        output_dir=tmp_path / "o",
        epochs=1,
    )
    worker = TrainingWorker(config)
    worker.command = lambda: [sys.executable, "-c", script]
    reasons = []
    lines = []
    results = []
    worker.abort_reason.connect(reasons.append)
    worker.progress.connect(lines.append)
    worker.finished_training.connect(lambda ok, msg: results.append(ok))
    worker.start()

    elapsed = 0
    while elapsed < 8000 and not results:
        qapp.processEvents()
        time.sleep(0.02)
        elapsed += 20

    assert reasons == [reason]
    assert any("Träningen avbröts" in line for line in lines)


def test_abort_line_round_trips():
    assert parse_abort_line(abort_line("Överträning")) == "Överträning"
    assert parse_abort_line("vanlig rad") is None
    assert parse_abort_line(f"{ABORT_MARKER}inte json") is None
