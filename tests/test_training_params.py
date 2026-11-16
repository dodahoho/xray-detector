"""Träningsparametrar: RF-DETR:s upplösning, workers och seed samt YOLO:s
hyperparametrar (TASK-91, TASK-92)."""

import json
import sys
import types
from types import SimpleNamespace

import pytest

from xray_detector.domain.training import (
    DEFAULT_BATCH,
    RFDETR_RESOLUTION_DIVISOR,
    TrainConfig,
    default_batch,
    rfdetr_resolution_error,
)

# --- RF-DETR:s upplösning (TASK-91) ---


def test_a_resolution_divisible_by_the_patch_grid_is_accepted():
    assert rfdetr_resolution_error(640) is None
    assert rfdetr_resolution_error(RFDETR_RESOLUTION_DIVISOR) is None


def test_a_resolution_off_the_patch_grid_is_rejected_with_a_clear_error():
    error = rfdetr_resolution_error(650)

    assert error is not None
    assert "650" in error
    assert str(RFDETR_RESOLUTION_DIVISOR) in error
    assert "patch_size" in error


def test_a_non_positive_resolution_is_rejected():
    assert rfdetr_resolution_error(0) is not None


def test_train_task_rejects_a_bad_rfdetr_resolution_before_starting(monkeypatch, tmp_path, capsys):
    """Felet ska komma innan körningskatalogen skapas (TASK-91)."""
    from xray_detector.infrastructure.training import train_task

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "train_task",
            "--dataset",
            str(tmp_path / "ds"),
            "--weights",
            "rfdetr-small",
            "--output",
            str(tmp_path / "out"),
            "--family",
            "rfdetr",
            "--imgsz",
            "650",
        ],
    )

    with pytest.raises(SystemExit) as exit_info:
        train_task.main()

    assert exit_info.value.code == 2
    assert "32" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


# --- Batch-default per familj (TASK-91) ---


def test_batch_default_differs_between_the_families():
    assert DEFAULT_BATCH["yolo"] == 16
    assert DEFAULT_BATCH["rfdetr"] == 4
    assert default_batch("yolo") == 16
    assert default_batch("rfdetr") == 4


def test_train_config_resolves_the_batch_from_the_family(tmp_path):
    yolo = TrainConfig(dataset_yaml=tmp_path / "d.yaml", weights="yolo26n.pt", output_dir=tmp_path)
    rfdetr = TrainConfig(
        dataset_yaml=tmp_path / "d.yaml",
        weights="rfdetr-large",
        output_dir=tmp_path,
        family="rfdetr",
    )

    assert yolo.batch_size() == 16
    assert rfdetr.batch_size() == 4


def test_an_explicit_batch_wins_over_the_family_default(tmp_path):
    config = TrainConfig(
        dataset_yaml=tmp_path / "d.yaml",
        weights="rfdetr-large",
        output_dir=tmp_path,
        batch=2,
        family="rfdetr",
    )

    assert config.batch_size() == 2


def test_training_view_follows_the_family_until_the_user_chooses(qapp, tmp_path):
    from PySide6.QtCore import QSettings

    from xray_detector.application.dataset_service import DatasetService
    from xray_detector.domain.config import AppConfig
    from xray_detector.ui.training_view import TrainingView

    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    view = TrainingView(config, DatasetService(config.dataset_dir), settings)

    assert view.batch_spin.value() == 16

    view.model_combo.setCurrentIndex(view.model_combo.findData("rfdetr-large"))
    assert view.batch_spin.value() == 4

    view.model_combo.setCurrentIndex(view.model_combo.findData("yolo26n"))
    assert view.batch_spin.value() == 16

    # ett eget val stannar kvar när familjen byts
    view.batch_spin.setValue(8)
    view.model_combo.setCurrentIndex(view.model_combo.findData("rfdetr-large"))
    assert view.batch_spin.value() == 8


def test_training_view_rejects_a_bad_rfdetr_resolution(qapp, tmp_path, monkeypatch):
    """Vyn avvisar storleken innan träningsprocessen startar (TASK-91)."""
    import importlib.util

    import numpy as np
    from PySide6.QtCore import QSettings

    from xray_detector.application.dataset_service import DatasetService
    from xray_detector.domain.config import AppConfig
    from xray_detector.domain.dataset import AnnotatedImage
    from xray_detector.ui.training_view import TrainingView

    real = importlib.util.find_spec
    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name, *args, **kwargs: object()
        if name == "rfdetr"
        else real(name, *args, **kwargs),
    )
    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    view = TrainingView(config, DatasetService(config.dataset_dir), settings)
    view.dataset_service.add_samples(
        [
            AnnotatedImage(
                np.zeros((20, 30, 3), np.uint8),
                [{"class_name": "kniv", "bbox": [1, 1, 4, 4]}],
            )
        ]
    )
    view.model_combo.setCurrentIndex(view.model_combo.findData("rfdetr-small"))
    view.imgsz_spin.setValue(650)
    messages = []
    view.status_changed.connect(messages.append)
    started = []
    view.training_service.create_worker = lambda cfg: started.append(cfg)

    view._on_start()

    assert not started
    assert messages and "32" in messages[0]


# --- YOLO:s hyperparametrar (TASK-92) ---


def _fake_ultralytics(monkeypatch, calls: list[dict]) -> None:
    """Ersätter ultralytics med en YOLO-klass som registrerar model.train-anropet."""

    class _FakeYolo:
        def __init__(self, weights):
            self.weights = weights
            self.callbacks = {}

        def add_callback(self, name, callback):
            self.callbacks[name] = callback

        def train(self, **kwargs):
            calls.append(kwargs)

    fake = types.ModuleType("ultralytics")
    fake.YOLO = _FakeYolo
    monkeypatch.setitem(sys.modules, "ultralytics", fake)


def _yolo_args(tmp_path, **overrides):
    values = {
        "family": "yolo",
        "dataset": str(tmp_path / "data.yaml"),
        "weights": "yolo26n.pt",
        "epochs": 5,
        "imgsz": 640,
        "batch": 16,
        "device": "cpu",
        "output_path": tmp_path / "out",
        "overfitting_guard": "off",
        "overfitting_patience": 10,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_yolo_training_sets_the_optimizer_and_seed_explicitly(monkeypatch, tmp_path):
    calls: list[dict] = []
    _fake_ultralytics(monkeypatch, calls)
    from xray_detector.infrastructure.training.progress import ProgressReporter
    from xray_detector.infrastructure.training.train_task import (
        _StopSignal,
        _train_yolo,
    )

    _train_yolo(
        _yolo_args(tmp_path),
        "cpu",
        _StopSignal(),
        ProgressReporter(emit=lambda line: None),
    )

    assert calls[0]["optimizer"] == "AdamW"
    assert calls[0]["lr0"] == 0.001
    assert calls[0]["cos_lr"] is True
    assert calls[0]["seed"] == 42
    assert calls[0]["deterministic"] is True


def test_yolo_augmentation_is_chosen_for_xray(monkeypatch, tmp_path):
    calls: list[dict] = []
    _fake_ultralytics(monkeypatch, calls)
    from xray_detector.infrastructure.training.progress import ProgressReporter
    from xray_detector.infrastructure.training.train_task import (
        _StopSignal,
        _train_yolo,
    )

    _train_yolo(
        _yolo_args(tmp_path),
        "cpu",
        _StopSignal(),
        ProgressReporter(emit=lambda line: None),
    )

    # rotation tillåts, mosaic är nedtonad och mättnadsändringen begränsad
    assert calls[0]["degrees"] == 30
    assert calls[0]["mosaic"] == 0.3
    assert calls[0]["close_mosaic"] == 15
    assert calls[0]["hsv_s"] == 0.2


def test_yolo_training_keeps_the_run_arguments(monkeypatch, tmp_path):
    calls: list[dict] = []
    _fake_ultralytics(monkeypatch, calls)
    from xray_detector.infrastructure.training.progress import ProgressReporter
    from xray_detector.infrastructure.training.train_task import (
        _StopSignal,
        _train_yolo,
    )

    _train_yolo(
        _yolo_args(tmp_path, epochs=7, imgsz=512, batch=8),
        "cpu",
        _StopSignal(),
        ProgressReporter(emit=lambda line: None),
    )

    assert (calls[0]["epochs"], calls[0]["imgsz"], calls[0]["batch"]) == (7, 512, 8)
    assert calls[0]["data"] == str(tmp_path / "data.yaml")


def test_the_hyperparameters_are_readable_from_the_manifest(tmp_path):
    """En genomförd körning ska gå att läsa av efteråt (TASK-92)."""
    from xray_detector.infrastructure.training.train_task import (
        MANIFEST_NAME,
        _RunState,
        _write_manifest,
    )

    run_dir = tmp_path / "korning"
    weights = run_dir / "yolo" / "weights" / "best.pt"
    weights.parent.mkdir(parents=True)
    weights.write_bytes(b"vikter")

    _write_manifest(_yolo_args(run_dir), run_dir, _RunState(status="completed"))

    manifest = json.loads((run_dir / MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["hyperparameters"]["optimizer"] == "AdamW"
    assert manifest["hyperparameters"]["mosaic"] == 0.3
    assert manifest["hyperparameters"]["seed"] == 42


def test_the_rfdetr_hyperparameters_are_readable_from_the_manifest(tmp_path):
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
        _yolo_args(run_dir, family="rfdetr", weights="rfdetr-small", workers=8, seed=42),
        run_dir,
        _RunState(status="completed"),
    )

    manifest = json.loads((run_dir / MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["hyperparameters"]["resolution"] == 640
    assert manifest["hyperparameters"]["num_workers"] == 8
    assert manifest["hyperparameters"]["seed"] == 42
