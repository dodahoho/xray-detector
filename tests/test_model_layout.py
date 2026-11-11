"""Modellvikternas placering under models/ (TASK-50)."""

import json
from pathlib import Path

import numpy as np
from PySide6.QtCore import QSettings

from xray_detector.application.app_config import apply_yaml_overrides
from xray_detector.application.dataset_service import DatasetService
from xray_detector.application.model_registry import (
    MODEL_SPECS,
    base_models,
    trained_models,
)
from xray_detector.domain.config import PROJECT_ROOT, AppConfig
from xray_detector.domain.dataset import AnnotatedImage


def _write_run(trained_dir: Path, run: str, weights_relative: str = "yolo26m/weights/best.pt") -> Path:
    """Skapar en träningskörning med manifest och vikter, som train_task gör."""
    run_dir = trained_dir / run
    weights = run_dir / weights_relative
    weights.parent.mkdir(parents=True, exist_ok=True)
    weights.write_bytes(b"vikter")
    manifest = {
        "base_weights": "yolo26m.pt",
        "weights_relative": weights_relative,
        "classes": ["kniv", "pistol"],
    }
    (run_dir / "training_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return weights


def _config(tmp_path: Path) -> AppConfig:
    config = AppConfig()
    config.data_dir = tmp_path / "data"
    config.models_dir = tmp_path / "models"
    config.ensure_dirs()
    return config


# --- Sökvägsuppslag (AC 1, 3, 7) ---


def test_models_dir_is_project_models_regardless_of_workdir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = AppConfig()
    assert config.models_dir == PROJECT_ROOT / "models"
    assert config.models_dir.is_absolute()
    assert config.trained_dir == config.models_dir / "trained"


def test_ensure_dirs_creates_models_and_trained(tmp_path):
    config = AppConfig()
    config.data_dir = tmp_path / "data"
    config.models_dir = tmp_path / "models"
    config.ensure_dirs()
    assert (tmp_path / "models").is_dir()
    assert (tmp_path / "models" / "trained").is_dir()


def test_yaml_models_dir_override(tmp_path):
    config = AppConfig()
    yaml = tmp_path / "config.yaml"

    yaml.write_text("models_dir: models\n", encoding="utf-8")
    assert apply_yaml_overrides(config, yaml)
    assert config.models_dir == PROJECT_ROOT / "models"

    absolute = tmp_path / "vikter"
    yaml.write_text(f"models_dir: {absolute.as_posix()}\n", encoding="utf-8")
    assert apply_yaml_overrides(config, yaml)
    assert config.models_dir == absolute


# --- Basvikter och egentränade vikter (AC 2, 6) ---


def test_base_models_keep_yolo_weights_under_models(tmp_path):
    specs = {spec.key: spec for spec in base_models(tmp_path)}
    assert set(specs) == {spec.key for spec in MODEL_SPECS}
    assert specs["yolo26m"].weights == str(tmp_path / "yolo26m.pt")
    assert specs["rfdetr-nano"].weights == "rfdetr-nano"


def test_trained_models_are_found_in_trained_dir(tmp_path):
    trained = tmp_path / "models" / "trained"
    weights = _write_run(trained, "v3")

    specs = trained_models(trained)
    assert [spec.key for spec in specs] == ["trained-v3"]
    assert specs[0].weights == str(weights)
    assert specs[0].family == "yolo"
    assert "v3" in specs[0].label


def test_trained_models_scan_each_run_dir(tmp_path):
    trained = tmp_path / "trained"
    _write_run(trained, "v3_20261111T1200")
    _write_run(trained, "v3_20261112T0900")
    assert len(trained_models(trained)) == 2


def test_trained_models_ignore_missing_weights(tmp_path):
    trained = tmp_path / "trained"
    run_dir = trained / "v4"
    run_dir.mkdir(parents=True)
    (run_dir / "training_manifest.json").write_text(
        json.dumps({"weights_relative": "saknas/weights/best.pt"}), encoding="utf-8"
    )
    assert trained_models(trained) == []


def test_base_and_trained_weights_do_not_collide(tmp_path):
    config = _config(tmp_path)
    _write_run(config.trained_dir, "v3")

    base = base_models(config.models_dir)
    trained = trained_models(config.trained_dir)
    assert not {spec.key for spec in base} & {spec.key for spec in trained}
    assert not {spec.weights for spec in base} & {spec.weights for spec in trained}
    for spec in trained:
        assert Path(spec.weights).is_relative_to(config.trained_dir)


# --- Modellväljaren (AC 4, 5) ---


def test_detection_view_lists_trained_model(qapp, tmp_path):
    from xray_detector.ui.detection_view import DetectionView

    config = _config(tmp_path)
    weights = _write_run(config.trained_dir, "v3")
    view = DetectionView(config, QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))

    keys = [view.model_combo.itemData(row) for row in range(view.model_combo.count())]
    assert "trained-v3" in keys
    assert view._specs["trained-v3"].weights == str(weights)


def test_trained_model_weights_are_used_for_detection(monkeypatch, tmp_path):
    from xray_detector.application import model_registry
    from xray_detector.infrastructure.detectors import yolo_detector

    captured = {}

    class FakeYolo:
        def __init__(self, weights, class_names, confidence_threshold):
            captured["weights"] = weights

    monkeypatch.setattr(yolo_detector, "YoloDetector", FakeYolo)
    trained = tmp_path / "trained"
    weights = _write_run(trained, "v3")

    model_registry.create_detector(trained_models(trained)[0], ["kniv"], 0.4)
    assert captured["weights"] == str(weights)


def test_training_view_writes_to_trained_dir(qapp, tmp_path):
    from xray_detector.ui.training_view import TrainingView

    config = _config(tmp_path)
    dataset = DatasetService(config.dataset_dir, config.classes)
    dataset.add_samples(
        1,
        [AnnotatedImage(np.zeros((20, 30, 3), np.uint8),
                        [{"class_name": "kniv", "bbox": [1, 1, 4, 4]}])],
    )
    view = TrainingView(config, dataset, QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
    view.refresh_versions()

    started = []
    view.training_service.create_worker = lambda cfg: started.append(cfg)
    view.model_combo.setCurrentIndex(view.model_combo.findData("yolo26m"))
    view.run_combo.setCurrentIndex(view.run_combo.findData("direct"))
    view._on_start()

    assert started, "ingen träning startades"
    assert started[0].output_dir == config.trained_dir / "v1"
    assert started[0].weights == str(config.models_dir / "yolo26m.pt")


# --- Gammal placering (AC 8) ---


def test_legacy_models_dir_is_reported_at_startup(tmp_path):
    from types import SimpleNamespace

    from xray_detector.app import _warn_about_legacy_models

    config = _config(tmp_path)
    legacy = config.data_dir / "models"
    (legacy / "v1").mkdir(parents=True)

    messages = []
    log = SimpleNamespace(warning=lambda message, *args: messages.append(message % args))
    _warn_about_legacy_models(config, log)

    assert len(messages) == 1
    assert str(legacy) in messages[0]
    assert str(config.trained_dir) in messages[0]


def test_empty_legacy_models_dir_is_silent(tmp_path):
    from types import SimpleNamespace

    from xray_detector.app import _warn_about_legacy_models

    config = _config(tmp_path)
    (config.data_dir / "models").mkdir(parents=True)

    messages = []
    log = SimpleNamespace(warning=lambda message, *args: messages.append(message % args))
    _warn_about_legacy_models(config, log)

    assert messages == []
