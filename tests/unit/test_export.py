from __future__ import annotations

import json

import yaml

from xray_detector.domain.annotation import AnnotationBox
from xray_detector.domain.detection import BBox
from xray_detector.infrastructure.dataset_store.coco_export import export_coco
from xray_detector.infrastructure.dataset_store.coco_store import CocoStore
from xray_detector.infrastructure.dataset_store.rfdetr_export import export_rfdetr
from xray_detector.infrastructure.dataset_store.yolo_export import export_yolo


def _make_store(tmp_path, frame, pairs: int = 4) -> CocoStore:
    store = CocoStore(tmp_path / "default", "default")
    for index in range(pairs):
        store.add_pair(
            {"cam0": frame.copy(), "cam1": frame.copy()},
            {
                "cam0": [AnnotationBox(BBox(10 + index, 10, 50 + index, 50), "part")],
                "cam1": [AnnotationBox(BBox(20, 20, 60, 60), "defect")],
            },
        )
    return store


def _pair_ids_by_split(split_dir):
    return {path.name.split("_")[0] for path in split_dir.glob("*.jpg")}


def test_yolo_export_is_pair_aware(tmp_path, frame):
    store = _make_store(tmp_path, frame)
    destination = tmp_path / "yolo"
    manifest = export_yolo(store, "v000004", destination, train_split=0.5, val_split=0.5, seed=7)

    assert manifest["format"] == "yolo"
    assert manifest["version"] == "v000004"
    assert manifest["image_count"] == 8
    assert manifest["annotation_count"] == 8

    train_pairs = _pair_ids_by_split(destination / "images" / "train")
    val_pairs = _pair_ids_by_split(destination / "images" / "val")
    assert train_pairs
    assert val_pairs
    assert not train_pairs & val_pairs

    label_files = list((destination / "labels" / "train").glob("*.txt"))
    assert label_files
    first_label = label_files[0].read_text(encoding="utf-8").strip()
    parts = first_label.split()
    assert len(parts) == 5
    assert 0.0 <= float(parts[1]) <= 1.0

    data = yaml.safe_load((destination / "data.yaml").read_text(encoding="utf-8"))
    assert data["names"] == {0: "part", 1: "defect"}
    assert (destination / "manifest.json").exists()


def test_coco_export_has_manifest(tmp_path, frame):
    store = _make_store(tmp_path, frame, pairs=2)
    destination = tmp_path / "coco"
    manifest = export_coco(store, "v000002", destination)

    assert manifest["format"] == "coco"
    assert manifest["annotation_count"] == 4
    assert manifest["image_count"] == 4
    coco = json.loads((destination / "annotations" / "instances.json").read_text(encoding="utf-8"))
    assert len(coco["images"]) == 4
    assert (destination / "manifest.json").exists()
    assert len(list((destination / "images").glob("*.jpg"))) == 4


def test_rfdetr_export_layout(tmp_path, frame):
    store = _make_store(tmp_path, frame, pairs=5)
    destination = tmp_path / "rfdetr"
    manifest = export_rfdetr(store, "v000005", destination, train_split=0.6, val_split=0.4)

    assert (destination / "train" / "_annotations.coco.json").exists()
    assert (destination / "valid" / "_annotations.coco.json").exists()
    assert manifest["splits"]["train"]["images"] > 0
    assert manifest["splits"]["valid"]["images"] > 0

    train = json.loads(
        (destination / "train" / "_annotations.coco.json").read_text(encoding="utf-8")
    )
    valid = json.loads(
        (destination / "valid" / "_annotations.coco.json").read_text(encoding="utf-8")
    )
    train_pairs = {image["pair_id"] for image in train["images"]}
    valid_pairs = {image["pair_id"] for image in valid["images"]}
    assert not train_pairs & valid_pairs
    assert manifest["class_names"] == ["part", "defect"]
