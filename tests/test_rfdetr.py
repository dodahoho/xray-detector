"""RF-DETR-stöd (TASK-11): exportformat, träningskommando och avstängning."""

import json

import numpy as np
import pytest

from xray_detector.application.dataset_service import DatasetService
from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.domain.training import TrainConfig


@pytest.fixture
def service(tmp_path) -> DatasetService:
    svc = DatasetService(tmp_path / "datasets")
    svc.set_classes(["kniv", "pistol"])
    for group in range(4):
        svc.add_samples([
            AnnotatedImage(np.full((30, 40, 3), 50 + group * 40, np.uint8),
                           [{"class_name": "kniv", "bbox": [2, 2, 8, 8]}])
            for _ in range(2)
        ])
    return svc


def test_export_rfdetr_layout(service, tmp_path):
    out = service.export_rfdetr(tmp_path / "exports")
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
        weights="rfdetr-small",
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
    view = TrainingView(config, DatasetService(config.dataset_dir), settings)

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


class _FakeDetections:
    """Minsta supervision.Detections: xyxy/class_id/confidence + data."""

    def __init__(self, xyxy, class_id, confidence, class_name):
        self.xyxy = np.array(xyxy, dtype=float)
        self.class_id = np.array(class_id, dtype=int)
        self.confidence = np.array(confidence, dtype=float)
        self.data = {"class_name": np.array(class_name, dtype=object)}


class _FakeRfDetrModel:
    """Ersätter RFDETRSmall: registrerar anropet och ger fasta detektioner."""

    class_names = ("kniv", "pistol")

    def __init__(self):
        self.calls = []

    def predict(self, image, threshold=0.5):
        self.calls.append((image, threshold))
        return _FakeDetections(
            xyxy=[[1, 2, 11, 22], [5, 6, 15, 16]],
            class_id=[0, 1],
            confidence=[0.9, 0.5],
            class_name=["kniv", ""],
        )


def test_rfdetr_detector_parses_supervision_detections(monkeypatch):
    """predict() ger supervision.Detections, inte en dict (TASK-24)."""
    import sys
    import types

    fake = types.ModuleType("rfdetr")
    fake.RFDETRSmall = _FakeRfDetrModel
    monkeypatch.setitem(sys.modules, "rfdetr", fake)

    from xray_detector.infrastructure.detectors.rfdetr_detector import RfDetrDetector

    detector = RfDetrDetector("rfdetr-small", 0.4)
    frame = np.full((20, 30, 3), (10, 20, 30), dtype=np.uint8)  # BGR
    detections = detector.detect(frame)

    assert [(d.class_name, round(d.confidence, 2)) for d in detections] == [
        ("kniv", 0.9),
        ("pistol", 0.5),  # tomt klassnamn fran modellen -> modellens klasslista
    ]
    assert (detections[0].x1, detections[0].y1, detections[0].x2, detections[0].y2) == (
        1.0, 2.0, 11.0, 22.0
    )
    image, threshold = detector.model.calls[0]
    assert threshold == 0.4
    assert tuple(image[0, 0]) == (30, 20, 10)  # BGR -> RGB innan predict


def _patch_rfdetr_presence(monkeypatch, present: bool) -> None:
    """Tvingar find_spec('rfdetr') till narvaro/franvaro oavsett miljo."""
    import importlib.util

    real = importlib.util.find_spec

    def fake(name, *args, **kwargs):
        if name == "rfdetr":
            return object() if present else None
        return real(name, *args, **kwargs)

    monkeypatch.setattr(importlib.util, "find_spec", fake)


def _detection_view(tmp_path, settings=None):
    from PySide6.QtCore import QSettings

    from xray_detector.domain.config import AppConfig
    from xray_detector.ui.detection_view import DetectionView

    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    if settings is None:
        settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    return DetectionView(config, settings)


def _rfdetr_row(view) -> int:
    rows = [i for i in range(view.model_combo.count())
            if str(view.model_combo.itemData(i)).startswith("rfdetr")]
    assert rows, "RF-DETR-posten saknas i kombon"
    return rows[0]


def test_detection_view_disables_rfdetr_without_package(qapp, tmp_path, monkeypatch):
    _patch_rfdetr_presence(monkeypatch, present=False)
    view = _detection_view(tmp_path)

    row = _rfdetr_row(view)
    assert not view.model_combo.model().item(row).isEnabled()
    assert "(rfdetr ej installerat)" in view.model_combo.itemText(row)


def test_detection_view_enables_rfdetr_with_package(qapp, tmp_path, monkeypatch):
    _patch_rfdetr_presence(monkeypatch, present=True)
    view = _detection_view(tmp_path)

    row = _rfdetr_row(view)
    assert view.model_combo.model().item(row).isEnabled()
    assert "(rfdetr ej installerat)" not in view.model_combo.itemText(row)


def test_detection_view_falls_back_from_unavailable_model(qapp, tmp_path, monkeypatch):
    """Sparat RF-DETR-val utan paket ska inte ge felladdning i statusbaren."""
    from PySide6.QtCore import QSettings

    _patch_rfdetr_presence(monkeypatch, present=False)
    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    settings.setValue("detection/model", "rfdetr-small")
    view = _detection_view(tmp_path, settings)
    errors = []
    view.error_occurred.connect(errors.append)

    view.restore_settings()

    assert view.model_combo.currentData() != "rfdetr-small"
    current = view.model_combo.model().item(view.model_combo.currentIndex())
    assert current.isEnabled()
    assert not [e for e in errors if "Kunde inte ladda modell" in e]


RFDETR_SIZES = ("rfdetr-nano", "rfdetr-small", "rfdetr-medium", "rfdetr-large")


def test_model_registry_lists_all_rfdetr_sizes():
    from xray_detector.application.model_registry import MODEL_SPECS

    specs = {spec.key: spec for spec in MODEL_SPECS}
    for key in RFDETR_SIZES:
        assert key in specs, key
        assert specs[key].family == "rfdetr"
        assert specs[key].weights == key


def test_rfdetr_variant_maps_every_size(monkeypatch):
    import sys
    import types

    from xray_detector.infrastructure.detectors.rfdetr_detector import (
        RFDETR_VARIANTS,
        rfdetr_variant,
    )

    fake = types.ModuleType("rfdetr")
    for class_name in RFDETR_VARIANTS.values():
        setattr(fake, class_name, type(class_name, (), {}))
    monkeypatch.setitem(sys.modules, "rfdetr", fake)

    for key, class_name in RFDETR_VARIANTS.items():
        assert rfdetr_variant(key).__name__ == class_name


def test_rfdetr_variant_rejects_unknown_size(monkeypatch):
    import sys
    import types

    import pytest

    from xray_detector.infrastructure.detectors.rfdetr_detector import rfdetr_variant

    monkeypatch.setitem(sys.modules, "rfdetr", types.ModuleType("rfdetr"))
    with pytest.raises(ValueError, match="Okänd RF-DETR-modell"):
        rfdetr_variant("rfdetr-huge")


def test_rfdetr_detector_uses_selected_size(monkeypatch):
    import sys
    import types

    from xray_detector.infrastructure.detectors.rfdetr_detector import RfDetrDetector

    class _FakeNano:
        class_names = ("kniv",)

        def predict(self, image, threshold=0.5):
            return _FakeDetections(xyxy=[], class_id=[], confidence=[], class_name=[])

    fake = types.ModuleType("rfdetr")
    fake.RFDETRNano = _FakeNano
    monkeypatch.setitem(sys.modules, "rfdetr", fake)

    detector = RfDetrDetector("rfdetr-nano", 0.4)
    assert isinstance(detector.model, _FakeNano)


def test_train_rfdetr_uses_selected_size(monkeypatch, tmp_path):
    import sys
    import types

    used = []

    class _FakeNano:
        def __init__(self):
            used.append(type(self).__name__)

        def train(self, **kwargs):
            return None

    fake = types.ModuleType("rfdetr")
    fake.RFDETRNano = _FakeNano
    monkeypatch.setitem(sys.modules, "rfdetr", fake)

    from xray_detector.infrastructure.training.train_task import _train_rfdetr

    args = types.SimpleNamespace(
        weights="rfdetr-nano",
        dataset=str(tmp_path / "ds"),
        epochs=1,
        batch=1,
        output_path=tmp_path / "out",
    )
    run_dir = _train_rfdetr(args, "cpu")

    assert used == ["_FakeNano"]
    assert run_dir == tmp_path / "out" / "rfdetr"


def test_detection_view_lists_all_rfdetr_sizes(qapp, tmp_path, monkeypatch):
    _patch_rfdetr_presence(monkeypatch, present=True)
    view = _detection_view(tmp_path)

    keys = [view.model_combo.itemData(i) for i in range(view.model_combo.count())]
    for key in RFDETR_SIZES:
        assert key in keys, key


def test_training_view_lists_all_rfdetr_sizes(qapp, tmp_path, monkeypatch):
    from PySide6.QtCore import QSettings

    from xray_detector.domain.config import AppConfig
    from xray_detector.ui.training_view import TrainingView

    _patch_rfdetr_presence(monkeypatch, present=True)
    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    view = TrainingView(config, DatasetService(config.dataset_dir), settings)

    weights = [view.model_combo.itemData(i) for i in range(view.model_combo.count())]
    for key in RFDETR_SIZES:
        assert key in weights, key
