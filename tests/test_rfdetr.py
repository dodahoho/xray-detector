"""RF-DETR-stöd (TASK-11): exportformat, träningskommando och avstängning."""

import json

import numpy as np
import pytest

from xray_detector.application.dataset_service import DatasetService
from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.domain.training import TrainConfig


@pytest.fixture
def service(tmp_path) -> DatasetService:
    svc = DatasetService(tmp_path / "datasets", ["kniv", "pistol"])
    for group in range(4):
        svc.add_samples(1, [
            AnnotatedImage(np.full((30, 40, 3), 50 + group * 40, np.uint8),
                           [{"class_name": "kniv", "bbox": [2, 2, 8, 8]}])
            for _ in range(2)
        ])
    return svc


def test_export_rfdetr_layout(service, tmp_path):
    out = service.export_rfdetr(1, tmp_path / "exports")
    for split in ("train", "valid", "test"):
        split_dir = out / split
        assert (split_dir / "_annotations.coco.json").exists(), split
        images = list((split_dir / "images").glob("*.png"))
        assert images, split
        coco = json.loads((split_dir / "_annotations.coco.json").read_text(encoding="utf-8"))
        assert len(coco["images"]) == len(images)
        assert len(coco["annotations"]) == len(images)
        assert [c["name"] for c in coco["categories"]] == ["kniv", "pistol"]
        assert all(img["file_name"].startswith("images/") for img in coco["images"])
    train = json.loads((out / "train" / "_annotations.coco.json").read_text(encoding="utf-8"))
    valid = json.loads((out / "valid" / "_annotations.coco.json").read_text(encoding="utf-8"))
    assert len(train["images"]) + len(valid["images"]) == 8
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["format"] == "rfdetr"
    assert manifest["num_train"] == len(train["images"])


def test_trainer_command_includes_family(tmp_path):
    from xray_detector.infrastructure.training.trainer import TrainingWorker

    config = TrainConfig(
        dataset_yaml=tmp_path / "d.yaml",
        weights="rfdetr-base",
        output_dir=tmp_path / "o",
        epochs=3,
        family="rfdetr",
    )
    command = TrainingWorker(config).command()
    assert "xray_detector.infrastructure.training.train_task" in command
    assert command[command.index("--family") + 1] == "rfdetr"


def test_family_defaults_to_yolo(tmp_path):
    from xray_detector.infrastructure.training.trainer import TrainingWorker

    config = TrainConfig(dataset_yaml=tmp_path / "d.yaml", weights="yolo26n.pt", output_dir=tmp_path / "o")
    assert config.family == "yolo"
    command = TrainingWorker(config).command()
    assert command[command.index("--family") + 1] == "yolo"


def test_training_view_disables_rfdetr_without_package(qapp, tmp_path, monkeypatch):
    from PySide6.QtCore import QSettings

    from xray_detector.domain.config import AppConfig
    from xray_detector.ui.training_view import TrainingView

    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    view = TrainingView(config, DatasetService(config.dataset_dir, config.classes), settings)

    import importlib.util

    if importlib.util.find_spec("rfdetr") is None:
        # paketet saknas i denna milj: posten ska vara avstangd
        row = [i for i in range(view.model_combo.count())
               if str(view.model_combo.itemData(i)).startswith("rfdetr")]
        assert row, "RF-DETR-posten saknas i kombon"
        assert not view.model_combo.model().item(row[0]).isEnabled()
        assert "(rfdetr ej installerat)" in view.model_combo.itemText(row[0])
    else:
        pytest.skip("rfdetr ar installerat; avstangningslagen kan inte testas har")
