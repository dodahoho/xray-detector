"""Träningens inlärningshastighet som justerbar parameter (TASK-162).

Små dataset överanpassas snabbt, så träningsvyn har ett eget fält för
inlärningshastigheten med 5e-5 som default. Värdet går till YOLO som ``lr0``
och till RF-DETR som ``lr``, och sparas i manifestets ``hyperparameters``.
"""

import json
import sys
import types

import numpy as np

from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.domain.training import DEFAULT_LEARNING_RATE, TrainConfig
from xray_detector.infrastructure.dataset_store.store import DatasetStore
from xray_detector.infrastructure.training.train_task import TrainArgs
from xray_detector.ui.training_view import TrainingView


def _view(config, settings) -> TrainingView:
    return TrainingView(config, DatasetStore(config.dataset_dir), settings)


def _sample() -> AnnotatedImage:
    return AnnotatedImage(
        np.zeros((20, 30, 3), np.uint8),
        [{"class_name": "kniv", "bbox": [1, 1, 4, 4]}],
    )


def _args(tmp_path, **overrides) -> TrainArgs:
    values = {
        "dataset": str(tmp_path / "data.yaml"),
        "weights": "yolo26n.pt",
        "epochs": 5,
        "imgsz": 640,
        "batch": 16,
        "device": "cpu",
        "output_path": tmp_path / "out",
        "overfitting_guard": "off",
    }
    values.update(overrides)
    return TrainArgs(**values)


def test_the_default_learning_rate_is_5e_5(tmp_path):
    assert DEFAULT_LEARNING_RATE == 5e-5
    config = TrainConfig(
        dataset_yaml=tmp_path / "d.yaml", weights="yolo26n.pt", output_dir=tmp_path
    )

    assert config.learning_rate == 5e-5


def test_the_worker_passes_the_learning_rate_to_the_training_process(tmp_path):
    from xray_detector.infrastructure.training.trainer import TrainingWorker

    config = TrainConfig(
        dataset_yaml=tmp_path / "d.yaml",
        weights="yolo26n.pt",
        output_dir=tmp_path / "o",
        learning_rate=0.0002,
    )
    command = TrainingWorker(config).command()

    assert command[command.index("--learning-rate") + 1] == "0.0002"


def test_yolo_training_uses_the_learning_rate_as_lr0(monkeypatch, tmp_path):
    calls: list[dict] = []

    class _FakeYolo:
        def __init__(self, weights):
            self.weights = weights

        def add_callback(self, name, callback):
            pass

        def train(self, **kwargs):
            calls.append(kwargs)

    fake = types.ModuleType("ultralytics")
    fake.YOLO = _FakeYolo
    monkeypatch.setitem(sys.modules, "ultralytics", fake)
    from xray_detector.infrastructure.training.progress import ProgressReporter
    from xray_detector.infrastructure.training.train_task import _train_yolo

    _train_yolo(
        _args(tmp_path, learning_rate=0.0002),
        "cpu",
        ProgressReporter(emit=lambda line: None),
    )

    assert calls[0]["lr0"] == 0.0002


def test_rfdetr_training_uses_the_learning_rate_as_lr(monkeypatch, tmp_path):
    trained: list[dict] = []

    class _FakeNano:
        def __init__(self, **kwargs):
            pass

        def train(self, **kwargs):
            trained.append(kwargs)

    fake = types.ModuleType("rfdetr")
    fake.RFDETRNano = _FakeNano
    monkeypatch.setitem(sys.modules, "rfdetr", fake)
    from xray_detector.infrastructure.training.train_task import _train_rfdetr

    _train_rfdetr(
        _args(tmp_path, family="rfdetr", weights="rfdetr-nano", learning_rate=0.0002),
        "cpu",
    )

    assert trained[0]["lr"] == 0.0002


def test_the_manifest_records_the_learning_rate(tmp_path):
    from xray_detector.infrastructure.training.train_task import (
        MANIFEST_NAME,
        _RunState,
        _write_manifest,
    )

    run_dir = tmp_path / "korning"
    weights = run_dir / "yolo" / "weights" / "best.pt"
    weights.parent.mkdir(parents=True)
    weights.write_bytes(b"vikter")

    _write_manifest(
        _args(run_dir, learning_rate=0.0002), run_dir, _RunState(status="completed")
    )

    manifest = json.loads((run_dir / MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["hyperparameters"]["lr0"] == 0.0002


def test_the_rfdetr_manifest_records_the_learning_rate(tmp_path):
    from xray_detector.infrastructure.training.train_task import (
        MANIFEST_NAME,
        _RunState,
        _write_manifest,
    )

    run_dir = tmp_path / "korning"
    weights = run_dir / "rfdetr" / "checkpoint_best_total.pth"
    weights.parent.mkdir(parents=True)
    weights.write_bytes(b"vikter")

    _write_manifest(
        _args(run_dir, family="rfdetr", weights="rfdetr-nano", learning_rate=0.0002),
        run_dir,
        _RunState(status="completed"),
    )

    manifest = json.loads((run_dir / MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["hyperparameters"]["lr"] == 0.0002


def test_the_training_view_starts_at_the_default_learning_rate(qapp, config, settings):
    view = _view(config, settings)

    assert view.lr_spin.value() == 5e-5


def test_the_learning_rate_is_saved_and_restored(qapp, config, settings):
    view = _view(config, settings)
    view.lr_spin.setValue(0.0002)
    view.save_settings()

    restored = _view(config, settings)
    restored.restore_settings()

    assert restored.lr_spin.value() == 0.0002


def test_the_view_passes_the_learning_rate_to_the_run(qapp, config, settings):
    service = DatasetStore(config.dataset_dir)
    service.add_samples([_sample()])
    view = _view(config, settings)
    view.lr_spin.setValue(0.0002)
    started = []
    view._start_direct = lambda cfg, export: started.append(cfg)

    view._on_start()

    assert started and started[0].learning_rate == 0.0002
