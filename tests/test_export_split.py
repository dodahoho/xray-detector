"""Enhetstester för YOLO-export och train/val-delning per fångstgrupp."""

import json
from pathlib import Path

import numpy as np

from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.infrastructure.dataset_store.export import (
    export_coco,
    export_rfdetr,
    export_yolo,
    group_count,
    train_val_counts,
    train_val_split,
)
from xray_detector.infrastructure.dataset_store.store import DatasetStore


def make_service(tmp_path) -> DatasetStore:
    service = DatasetStore(tmp_path / "datasets")
    service.set_classes(["kniv", "pistol"])
    return service


def add_groups(svc: DatasetStore, groups: int, per_group: int = 2) -> None:
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
    images = [
        {"id": 1, "group": 1}, {"id": 2, "group": 1},
        {"id": 3, "group": 2}, {"id": 4, "group": 2},
        {"id": 5, "group": 3}, {"id": 6, "group": 3},
    ]
    train, val = train_val_split(images)
    train_ids = {image["id"] for image in train}
    val_ids = {image["id"] for image in val}
    assert train_ids | val_ids == {1, 2, 3, 4, 5, 6}
    assert not (train_ids & val_ids)
    for left, right in ((1, 2), (3, 4), (5, 6)):
        assert (left in train_ids) == (right in train_ids)
        assert (left in val_ids) == (right in val_ids)


def test_export_yolo_writes_a_complete_dataset(tmp_path):
    """Exporten kopierar bilder, labels och metadata så den går att importera (TASK-159)."""
    svc = make_service(tmp_path)
    add_groups(svc, 6)
    out = export_yolo(svc, tmp_path / "exports").parent

    train_lines = (out / "train.txt").read_text(encoding="utf-8").splitlines()
    val_lines = (out / "val.txt").read_text(encoding="utf-8").splitlines()
    assert len(train_lines) == 10
    assert len(val_lines) == 2
    # listan pekar på exportens egna kopior, så exporten är en egen samling
    assert all(Path(line).is_file() for line in train_lines + val_lines)
    assert all(Path(line).parent == (out / "images").resolve() for line in train_lines)
    assert len(list((out / "images").glob("*.png"))) == 12
    assert len(list((out / "labels").glob("*.txt"))) == 12

    yaml_text = (out / "data.yaml").read_text(encoding="utf-8")
    assert "train: train.txt" in yaml_text
    assert "val: val.txt" in yaml_text
    assert 'names: ["kniv", "pistol"]' in yaml_text

    # dataset.json följer med, eftersom YOLO-formatet saknar bildpar
    metadata = json.loads((out / "dataset.json").read_text(encoding="utf-8"))
    assert len(metadata["images"]) == 12
    assert {image["group"] for image in metadata["images"]} == {1, 2, 3, 4, 5, 6}

    # label-filen ligger i exporten, där ultralytics hittar den
    label = (out / "labels" / "img_000001.txt").read_text(encoding="utf-8")
    assert label.startswith("0 ")
    assert len(label.strip().splitlines()) == 1


def test_export_yolo_group_integrity(tmp_path):
    svc = make_service(tmp_path)
    add_groups(svc, 6)
    out = export_yolo(svc, tmp_path / "exports").parent

    dataset = svc.load_dataset()
    group_of = {image["file_name"]: image.get("group") for image in dataset["images"]}

    def groups(name: str) -> set:
        lines = (out / name).read_text(encoding="utf-8").splitlines()
        return {group_of[Path(line).name] for line in lines}

    assert not (groups("train.txt") & groups("val.txt"))


def test_manifest_contains_split_counts(tmp_path):
    svc = make_service(tmp_path)
    add_groups(svc, 6)
    out = export_yolo(svc, tmp_path / "exports").parent
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["num_train"] == 10
    assert manifest["num_val"] == 2
    assert manifest["num_images"] == 12


def test_export_coco_copies_images_and_dataset(tmp_path):
    svc = make_service(tmp_path)
    add_groups(svc, 2)
    out = export_coco(svc, tmp_path / "exports")
    assert len(list((out / "images").glob("*.png"))) == 4
    dataset = json.loads((out / "dataset.json").read_text(encoding="utf-8"))
    assert len(dataset["images"]) == 4


def test_export_replaces_the_lists_from_an_earlier_export(tmp_path):
    """En ny export får inte lämna kvar bilder som raderats ur datasetet."""
    svc = make_service(tmp_path)
    add_groups(svc, 2)
    export_yolo(svc, tmp_path / "exports")
    svc.delete_images([image["id"] for image in svc.load_dataset()["images"][:2]])

    out = export_yolo(svc, tmp_path / "exports").parent

    lines = (out / "train.txt").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert all(Path(line).is_file() for line in lines)


def test_split_ratio_controls_the_group_counts():
    """Andelen räknas i bildpar, så 50 % av tio par ger fem par per del (TASK-72)."""
    images = [{"id": i, "group": i} for i in range(1, 11)]

    train, val = train_val_split(images, 0.5)

    assert (group_count(train), group_count(val)) == (5, 5)


def test_export_yolo_uses_the_ratio(tmp_path):
    svc = make_service(tmp_path)
    add_groups(svc, 6)

    out = export_yolo(svc, tmp_path / "exports", 0.5).parent

    assert len((out / "train.txt").read_text(encoding="utf-8").splitlines()) == 6
    assert len((out / "val.txt").read_text(encoding="utf-8").splitlines()) == 6


def test_export_rfdetr_uses_the_ratio(tmp_path):
    svc = make_service(tmp_path)
    add_groups(svc, 6)

    out = export_rfdetr(svc, tmp_path / "exports", 0.5)

    train = json.loads((out / "train" / "_annotations.coco.json").read_text(encoding="utf-8"))
    valid = json.loads((out / "valid" / "_annotations.coco.json").read_text(encoding="utf-8"))
    test = json.loads((out / "test" / "_annotations.coco.json").read_text(encoding="utf-8"))
    assert len(train["images"]) == 6
    # resten delas mellan valid och test i stället för att test kopierar valid
    assert len(valid["images"]) + len(test["images"]) == 6


def test_service_train_val_counts(tmp_path):
    """Träningsvyns redovisning räknar bildpar, inte enskilda bilder (TASK-72)."""
    svc = make_service(tmp_path)
    add_groups(svc, 6)
    assert train_val_counts(svc) == (5, 1)
    assert train_val_counts(svc, 0.5) == (3, 3)


# --- RF-DETR:s test-del (TASK-93) ---


def _split_ids(out, split: str) -> set[int]:
    coco = json.loads((out / split / "_annotations.coco.json").read_text(encoding="utf-8"))
    return {image["id"] for image in coco["images"]}


def test_rfdetr_test_split_is_not_a_copy_of_valid(tmp_path):
    """Test ska vara egna bilder, inte samma som val (TASK-93)."""
    svc = make_service(tmp_path)
    add_groups(svc, 6)

    out = export_rfdetr(svc, tmp_path / "exports")

    train, valid, test = (_split_ids(out, name) for name in ("train", "valid", "test"))
    assert test, "test-delen är tom"
    assert not (test & valid)
    assert not (test & train)
    assert not (valid & train)


def test_rfdetr_manifest_counts_the_test_split(tmp_path):
    svc = make_service(tmp_path)
    add_groups(svc, 6)

    out = export_rfdetr(svc, tmp_path / "exports")

    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["num_test"] == len(_split_ids(out, "test"))
    assert manifest["num_test"] > 0


def test_rfdetr_split_is_reproducible(tmp_path):
    svc = make_service(tmp_path)
    add_groups(svc, 8)

    first = export_rfdetr(svc, tmp_path / "a")
    second = export_rfdetr(svc, tmp_path / "b")

    for split in ("train", "valid", "test"):
        assert _split_ids(first, split) == _split_ids(second, split)


def test_rfdetr_split_keeps_the_image_pairs_together(tmp_path):
    svc = make_service(tmp_path)
    add_groups(svc, 6)

    out = export_rfdetr(svc, tmp_path / "exports")

    dataset = svc.load_dataset()
    group_of = {image["id"]: image.get("group") for image in dataset["images"]}
    split_of_group: dict[object, str] = {}
    for split in ("train", "valid", "test"):
        for image_id in _split_ids(out, split):
            group = group_of[image_id]
            assert split_of_group.setdefault(group, split) == split, (
                f"grupp {group} ligger i både {split_of_group[group]} och {split}"
            )


def test_rfdetr_with_two_groups_has_no_test_split(tmp_path):
    """Med färre än tre grupper går tre delmängder inte att fylla (TASK-93)."""
    svc = make_service(tmp_path)
    add_groups(svc, 2)

    out = export_rfdetr(svc, tmp_path / "exports")

    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["num_test"] == 0
    assert manifest["num_val"] == 2


# --- Stratifierad delning (TASK-94) ---


def _classes(images: list[dict]) -> set[str]:
    return {
        annotation["class_name"]
        for image in images
        for annotation in image.get("annotations") or []
    }


def test_rare_class_lands_in_both_train_and_val():
    """En klass med få exempel får inte hamna helt utanför val (TASK-94)."""
    images = [
        {
            "id": group,
            "group": group,
            "annotations": [{"class_name": "kniv", "bbox": [0, 0, 1, 1]}],
        }
        for group in range(1, 9)
    ]
    images += [
        {
            "id": group,
            "group": group,
            "annotations": [{"class_name": "pistol", "bbox": [0, 0, 1, 1]}],
        }
        for group in (9, 10)
    ]

    train, val = train_val_split(images)

    assert _classes(train) == {"kniv", "pistol"}
    assert _classes(val) == {"kniv", "pistol"}


def test_stratified_split_still_keeps_the_groups_together():
    images = [
        {
            "id": group,
            "group": group,
            "annotations": [{"class_name": "kniv", "bbox": [0, 0, 1, 1]}],
        }
        for group in range(1, 11)
    ]
    images += [
        {
            "id": group,
            "group": group,
            "annotations": [{"class_name": "pistol", "bbox": [0, 0, 1, 1]}],
        }
        for group in (11, 12)
    ]

    train, val = train_val_split(images)

    train_groups = {image["group"] for image in train}
    val_groups = {image["group"] for image in val}
    assert not (train_groups & val_groups)
    assert train_groups | val_groups == set(range(1, 13))


def test_stratified_split_is_reproducible():
    images = [
        {
            "id": group,
            "group": group,
            "annotations": [{"class_name": "kniv", "bbox": [0, 0, 1, 1]}],
        }
        for group in range(1, 21)
    ]

    first = train_val_split(images)
    second = train_val_split(images)

    assert [image["id"] for image in first[0]] == [image["id"] for image in second[0]]
    assert [image["id"] for image in first[1]] == [image["id"] for image in second[1]]


# --- Syntetiska bilder i delningen (TASK-111) ---


def _original(image_id: int, group: int) -> dict:
    return {
        "id": image_id,
        "group": group,
        "annotations": [{"class_name": "kniv", "bbox": [1, 1, 6, 6]}],
    }


def _synthetic(image_id: int, group: int, source: int) -> dict:
    """En variation: egen fångstgrupp, men source pekar på ursprungsbilden."""
    return {
        "id": image_id,
        "group": group,
        "synthetic": True,
        "source": source,
        "annotations": [{"class_name": "kniv", "bbox": [1, 1, 6, 6]}],
    }


def _originals(count: int) -> list[dict]:
    return [_original(image_id, group) for group, image_id in enumerate(range(1, count + 1), 1)]


def _variations(originals: list[dict]) -> list[dict]:
    return [
        _synthetic(100 + index, 50 + index, source=image["id"])
        for index, image in enumerate(originals)
    ]


def test_synthetic_images_follow_their_origin_into_the_split():
    """En syntetisk bild hamnar alltid i samma del som sitt ursprung (TASK-111)."""
    originals = _originals(12)
    variations = _variations(originals)

    for seed in range(5):
        train, val = train_val_split(originals + variations, 0.5, seed)
        split_of = {image["id"]: "train" for image in train}
        split_of.update({image["id"]: "val" for image in val})
        for variation in variations:
            assert split_of[variation["id"]] == split_of[variation["source"]], seed


def test_group_count_counts_original_pairs_only():
    images = [
        {"id": 1, "group": 1},
        {"id": 2, "group": 1},
        _synthetic(3, 7, source=1),
        _synthetic(4, 8, source=2),
    ]

    assert group_count(images) == 1


def test_split_is_unchanged_when_the_dataset_is_extended():
    """Utökningen får inte flytta ett enda original mellan train och val (TASK-111)."""
    originals = _originals(12)
    variations = _variations(originals)

    before = train_val_split(originals, 0.5, 7)
    after = train_val_split(originals + variations, 0.5, 7)

    assert [[image["id"] for image in split] for split in before] == [
        [image["id"] for image in split if not image.get("synthetic")] for split in after
    ]


def test_synthetic_without_its_origin_keeps_its_own_group():
    """Saknas ursprunget i listan får bilden ingen grupp att följa (TASK-111)."""
    images = [{"id": 1, "group": 1}, _synthetic(2, 9, source=404)]

    assert group_count(images) == 2
