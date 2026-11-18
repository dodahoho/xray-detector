"""Tidigt stopp av träningen med ramverkens egna early stopping (TASK-46, TASK-118)."""

import json
import time
from pathlib import Path

from xray_detector.domain.training import TrainConfig
from xray_detector.infrastructure.training.epoch_metrics import (
    ABORT_MARKER,
    abort_line,
    parse_abort_line,
)
from xray_detector.infrastructure.training.train_task import TrainArgs


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
    return TrainArgs(**values)


def _wait_for(predicate, timeout_s=5.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


# --- Tidigt stopp avgörs efter träningen (TASK-118) ---


def test_a_short_run_without_the_guard_is_completed(tmp_path):
    """Utan early stopping är färre epoker ingen tidig avstängning."""
    from xray_detector.infrastructure.training.train_task import (
        _finish_state,
        _RunState,
    )

    state = _RunState(epochs_completed=7)

    _finish_state(_args(tmp_path, overfitting_guard="off"), state)

    assert state.status == "completed"
    assert state.stop_reason is None


def test_a_run_without_any_reported_epoch_is_completed(tmp_path):
    """En metrics-fil som inte gick att läsa får inte se ut som ett stopp."""
    from xray_detector.infrastructure.training.train_task import (
        _finish_state,
        _RunState,
    )

    state = _RunState()

    _finish_state(_args(tmp_path), state)

    assert state.status == "completed"


# --- Rapportören följer epokerna (TASK-44, TASK-118) ---


def test_reporter_tracks_the_completed_epochs(tmp_path):
    from xray_detector.infrastructure.training.train_task import (
        _RunState,
        _start_reporter,
    )

    metrics_path = tmp_path / "yolo" / "results.csv"
    metrics_path.parent.mkdir(parents=True)
    metrics_path.write_text(
        "epoch,train/box_loss,metrics/mAP50-95(B)\n", encoding="utf-8"
    )
    state = _RunState()
    reporter = _start_reporter(_args(tmp_path), tmp_path, state)
    try:
        with open(metrics_path, "a", encoding="utf-8") as file:
            file.writelines(
                f"{epoch},{3.0 - epoch * 0.2},0.3\n" for epoch in range(1, 4)
            )
        assert _wait_for(lambda: state.epochs_completed == 3)
    finally:
        reporter.stop()
        reporter.join(timeout=5)

    assert state.epochs_completed == 3
    assert state.metrics["map50_95"] == 0.3


def test_manifest_records_the_abort_reason(tmp_path):
    from xray_detector.infrastructure.training.train_task import (
        _RunState,
        _write_manifest,
    )

    run_dir = tmp_path / "korning"
    weights = run_dir / "yolo" / "weights" / "best.pt"
    weights.parent.mkdir(parents=True)
    weights.write_bytes(b"vikter")
    state = _RunState(
        status="aborted",
        reason="Tidigt stopp: valvärdet förbättrades inte under de senaste 2 epokerna",
        epochs_completed=7,
    )

    _write_manifest(_args(run_dir), run_dir, state)

    manifest = json.loads((run_dir / "training_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "aborted"
    assert manifest["abort_reason"].startswith("Tidigt stopp")
    assert manifest["epochs_completed"] == 7


# --- Träningsprocessen (TASK-118) ---


def _fake_ultralytics(monkeypatch, epochs_written: int) -> None:
    """Ersätter ultralytics med en YOLO som skriver färre epoker än begärt."""

    class _FakeYolo:
        def __init__(self, weights):
            self.weights = weights

        def add_callback(self, name, callback):
            pass

        def train(self, **kwargs):
            run_dir = Path(kwargs["project"]) / kwargs["name"]
            run_dir.mkdir(parents=True, exist_ok=True)
            rows = "".join(
                f"{epoch},{3.0 - epoch * 0.2},0.3\n"
                for epoch in range(1, epochs_written + 1)
            )
            (run_dir / "results.csv").write_text(
                "epoch,train/box_loss,metrics/mAP50-95(B)\n" + rows, encoding="utf-8"
            )
            weights = run_dir / "weights" / "best.pt"
            weights.parent.mkdir(parents=True, exist_ok=True)
            weights.write_bytes(b"vikter")

    import sys
    import types

    fake = types.ModuleType("ultralytics")
    fake.YOLO = _FakeYolo
    monkeypatch.setitem(sys.modules, "ultralytics", fake)


def _run_main(monkeypatch, tmp_path, *extra: str) -> None:
    import sys

    from xray_detector.infrastructure.training import train_task

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "train_task",
            "--dataset",
            str(tmp_path / "data.yaml"),
            "--weights",
            "yolo26n.pt",
            "--output",
            str(tmp_path / "out"),
            "--epochs",
            "20",
            "--device",
            "cpu",
            *extra,
        ],
    )
    train_task.main()


def test_main_reports_the_frameworks_early_stop(monkeypatch, tmp_path, capsys):
    _fake_ultralytics(monkeypatch, epochs_written=2)

    _run_main(monkeypatch, tmp_path, "--overfitting-patience", "2")

    out = capsys.readouterr().out
    assert any(line.startswith(ABORT_MARKER) for line in out.splitlines())
    manifest = json.loads(
        (tmp_path / "out" / "training_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["status"] == "aborted"
    assert manifest["stop_reason"] == "overfitting"
    assert manifest["epochs_completed"] == 2


def test_main_completes_a_run_that_used_all_epochs(monkeypatch, tmp_path, capsys):
    _fake_ultralytics(monkeypatch, epochs_written=20)

    _run_main(monkeypatch, tmp_path)

    out = capsys.readouterr().out
    assert not any(line.startswith(ABORT_MARKER) for line in out.splitlines())
    manifest = json.loads(
        (tmp_path / "out" / "training_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["status"] == "completed"
    assert manifest["stop_reason"] is None


def test_rfdetr_gets_early_stopping_when_the_guard_is_on(monkeypatch, tmp_path):
    import sys
    import types

    captured = {}

    class _FakeNano:
        def __init__(self, **kwargs):
            pass

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
        def __init__(self, **kwargs):
            pass

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

    assert captured["early_stopping"] is False


# --- GUI:t (AC 1, 2, 3, 6, 9) ---


def _training_view(qapp, tmp_path, settings=None):
    from PySide6.QtCore import QSettings

    from xray_detector.domain.config import AppConfig
    from xray_detector.infrastructure.dataset_store.store import DatasetStore
    from xray_detector.ui.training_view import TrainingView

    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    if settings is None:
        settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    return TrainingView(config, DatasetStore(config.dataset_dir), settings)


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
    view.dataset_store.add_samples(
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

    view._on_abort_reason("Tidigt stopp: valvärdet förbättrades inte sedan epok 2")

    assert view.epoch_label.text().startswith("Avbruten:")
    assert "epok 2" in view.epoch_label.text()
    assert messages and "Tidigt stopp" in messages[0]


def test_worker_emits_the_abort_reason(qapp, tmp_path):
    import sys

    from xray_detector.infrastructure.training.trainer import TrainingWorker

    reason = "Tidigt stopp: valvärdet förbättrades inte sedan epok 2"
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
