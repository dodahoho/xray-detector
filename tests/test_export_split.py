"""Enhetstester för YOLO-export och train/val-delning per fångstgrupp."""

import json

import numpy as np

from xray_detector.application.dataset_service import DatasetService
from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.infrastructure.dataset_store.export import (
    group_count,
    train_val_split,
)


def make_service(tmp_path) -> DatasetService:
    service = DatasetService(tmp_path / "datasets")
    service.set_classes(["kniv", "pistol"])
    return service


def add_groups(svc: DatasetService, groups: int, per_group: int = 2) -> None:
    for group in range(groups):
        samples = [
            AnnotatedImage(
                np.full((32, 40, 3), 40 + group * 15, dtype=np.uint8),
                [{"class_name": "kniv", "bbox": [1, 1, 6, 6]}],
            )
            for _ in range(per_group)
        ]
        svc.add_samples(samples)


def test_split_is_group_aware():
    coco = {"images": [
        {"id": 1, "group": 1}, {"id": 2, "group": 1},
        {"id": 3, "group": 2}, {"id": 4, "group": 2},
        {"id": 5, "group": 3}, {"id": 6, "group": 3},
    ]}
    train, val = train_val_split(coco)
    train_ids = {image["id"] for image in train}
    val_ids = {image["id"] for image in val}
    assert train_ids | val_ids == {1, 2, 3, 4, 5, 6}
    assert not (train_ids & val_ids)
    for left, right in ((1, 2), (3, 4), (5, 6)):
        assert (left in train_ids) == (right in train_ids)
        assert (left in val_ids) == (right in val_ids)


def test_split_is_reproducible():
    coco = {"images": [{"id": i, "group": i} for i in range(1, 21)]}
    first = train_val_split(coco)
    second = train_val_split(coco)
    assert [image["id"] for image in first[0]] == [image["id"] for image in second[0]]
    assert [image["id"] for image in first[1]] == [image["id"] for image in second[1]]


def test_export_yolo_writes_split_labels_and_yaml(tmp_path):
    svc = make_service(tmp_path)
    add_groups(svc, 6)
    out = svc.export_yolo(tmp_path / "exports")

    train_images = list((out / "images" / "train").glob("*.png"))
    val_images = list((out / "images" / "val").glob("*.png"))
    assert len(train_images) == 10
    assert len(val_images) == 2
    assert len(list((out / "labels" / "train").glob("*.txt"))) == 10
    assert len(list((out / "labels" / "val").glob("*.txt"))) == 2

    yaml_text = (out / "data.yaml").read_text(encoding="utf-8")
    assert "train: images/train" in yaml_text
    assert "val: images/val" in yaml_text
    assert "names: ['kniv', 'pistol']" in yaml_text

    label = (out / "labels" / "train" / "img_000001.txt").read_text(encoding="utf-8")
    assert label.startswith("0 ")
    assert len(label.strip().splitlines()) == 1


def test_export_yolo_group_integrity(tmp_path):
    svc = make_service(tmp_path)
    add_groups(svc, 6)
    out = svc.export_yolo(tmp_path / "exports")

    coco = svc.load_coco()
    group_of = {image["id"]: image.get("group") for image in coco["images"]}
    train_groups = {group_of[int(p.stem.split("_")[1])] for p in (out / "images" / "train").glob("*.png")}
    val_groups = {group_of[int(p.stem.split("_")[1])] for p in (out / "images" / "val").glob("*.png")}
    assert not (train_groups & val_groups)


def test_manifest_contains_split_counts(tmp_path):
    svc = make_service(tmp_path)
    add_groups(svc, 6)
    out = svc.export_yolo(tmp_path / "exports")
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["num_train"] == 10
    assert manifest["num_val"] == 2
    assert manifest["num_images"] == 12


def test_export_coco_copies_images_and_dataset(tmp_path):
    svc = make_service(tmp_path)
    add_groups(svc, 2)
    out = svc.export_coco(tmp_path / "exports")
    assert len(list((out / "images").glob("*.png"))) == 4
    dataset = json.loads((out / "dataset.json").read_text(encoding="utf-8"))
    assert len(dataset["images"]) == 4


def test_export_replaces_images_from_an_earlier_export(tmp_path):
    """En ny export får inte lämna kvar bilder som raderats ur datasetet."""
    svc = make_service(tmp_path)
    add_groups(svc, 2)
    svc.export_yolo(tmp_path / "exports")
    svc.delete_images([image["id"] for image in svc.load_coco()["images"][:2]])

    out = svc.export_yolo(tmp_path / "exports")

    assert len(list((out / "images" / "train").glob("*.png"))) == 2
    assert len(list((out / "labels" / "train").glob("*.txt"))) == 2


def test_split_ratio_controls_the_group_counts():
    """Andelen räknas i bildpar, så 50 % av tio par ger fem par per del (TASK-72)."""
    coco = {"images": [{"id": i, "group": i} for i in range(1, 11)]}

    train, val = train_val_split(coco, 0.5)

    assert (group_count(train), group_count(val)) == (5, 5)


def test_export_yolo_uses_the_ratio(tmp_path):
    svc = make_service(tmp_path)
    add_groups(svc, 6)

    out = svc.export_yolo(tmp_path / "exports", 0.5)

    assert len(list((out / "images" / "train").glob("*.png"))) == 6
    assert len(list((out / "images" / "val").glob("*.png"))) == 6


def test_export_rfdetr_uses_the_ratio(tmp_path):
    svc = make_service(tmp_path)
    add_groups(svc, 6)

    out = svc.export_rfdetr(tmp_path / "exports", 0.5)

    train = json.loads((out / "train" / "_annotations.coco.json").read_text(encoding="utf-8"))
    valid = json.loads((out / "valid" / "_annotations.coco.json").read_text(encoding="utf-8"))
    assert (len(train["images"]), len(valid["images"])) == (6, 6)


def test_service_train_val_counts(tmp_path):
    """Träningsvyns redovisning räknar bildpar, inte enskilda bilder (TASK-72)."""
    svc = make_service(tmp_path)
    add_groups(svc, 6)
    assert svc.train_val_counts() == (5, 1)
    assert svc.train_val_counts(0.5) == (3, 3)
