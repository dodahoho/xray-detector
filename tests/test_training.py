from __future__ import annotations

import json

from xray_detector.models import Detection

from xray_detector.training.manifest import read_model_metadata
from xray_detector.training.dataset_converter import prepare_yolo_dataset
from xray_detector.training.trainer import (
    TrainingParameters,
    finalize_training,
    prepare_training,
)


def test_prepare_yolo_dataset_splits_groups(paths, store, capture_factory) -> None:
    for index in range(6):
        store.add_capture(
            capture_factory(index),
            {"left": [Detection(10, 10, 40, 50, 0, "skruv")], "right": []},
        )
    info = prepare_yolo_dataset(store, paths.training / "converted")
    assert info.train_images + info.val_images == 12
    assert info.val_images > 0
    assert info.data_yaml.exists()
    text = info.data_yaml.read_text(encoding="utf-8")
    assert "nc: 1" in text
    assert '0: "skruv"' in text
    assert len(list((paths.training / "converted" / "images" / "train").glob("*"))) == info.train_images


def test_prepare_and_finalize_training(paths, store, capture_factory) -> None:
    for index in range(5):
        store.add_capture(
            capture_factory(index),
            {"left": [Detection(10, 10, 40, 50, 0, "skruv")], "right": []},
        )
    plan = prepare_training(
        store,
        "yolo11n.pt",
        paths.training,
        TrainingParameters(epochs=1, imgsz=64, batch=1, workers=0),
        run_id="run-test",
    )
    assert plan.dataset_metadata.version == "1.0.1"
    assert plan.result_json.parent == plan.run_dir
    assert "--epochs" in plan.command

    best = plan.run_dir / "fake-best.pt"
    best.write_bytes(b"fake weights")
    plan.result_json.write_text(
        json.dumps({"best": str(best), "metrics": {"mAP50": 0.5}}),
        encoding="utf-8",
    )
    metadata, weights = finalize_training(plan, paths.models)
    assert weights.exists()
    assert weights.read_bytes() == b"fake weights"
    assert metadata.dataset_id == "default"
    assert metadata.dataset_version == plan.dataset_metadata.version
    assert metadata.metrics["mAP50"] == 0.5
    stored = read_model_metadata(weights.parent / "metadata.json")
    assert stored.dataset_version == metadata.dataset_version
    assert stored.weights == "best.pt"
