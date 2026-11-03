from __future__ import annotations

import json

from xray_detector.application.model_registry import ModelRegistry
from xray_detector.config import AppConfig


def test_trained_model_is_discovered(tmp_path):
    config = AppConfig.load(tmp_path / "config.yaml")
    config.app.data_root = str(tmp_path / "data")
    config.ensure_dirs()

    run_dir = config.models_dir / "myrun" / "v000002_20260101_120000"
    run_dir.mkdir(parents=True)
    weights = run_dir / "best.pt"
    weights.write_bytes(b"fake")
    manifest = {
        "model_id": "myrun:v000002",
        "run_name": "myrun",
        "family": "yolo",
        "dataset_version": "v000002",
        "class_names": ["part", "defect"],
        "weights": {"best": str(weights), "last": str(weights)},
    }
    (run_dir / "training_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    registry = ModelRegistry(config)
    models = {model.id: model for model in registry.list_models()}
    assert "yolo26n" in models
    assert "rfdetr-base" in models
    trained = models["myrun:v000002"]
    assert trained.trained
    assert trained.classes == {0: "part", 1: "defect"}
    assert trained.path == weights
    assert registry.get("myrun:v000002").family == "yolo"
