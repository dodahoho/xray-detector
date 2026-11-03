from __future__ import annotations

import pytest

from xray_detector.dataset.coco import (
    Annotation,
    Category,
    CocoDataset,
    ImageRecord,
    read_coco,
    write_coco,
)


def make_dataset() -> CocoDataset:
    return CocoDataset(
        images=[ImageRecord(1, "images/a.png", 100, 80, "g1", "left")],
        annotations=[
            Annotation(1, 1, 1, [10, 10, 20, 20], 400),
            Annotation(2, 1, 2, [40, 40, 10, 10], 100, score=0.5),
        ],
        categories=[Category(1, "skruv"), Category(2, "mutter")],
    )


def test_roundtrip(tmp_path) -> None:
    path = tmp_path / "annotations.json"
    dataset = make_dataset()
    write_coco(dataset, path)
    loaded = read_coco(path)
    assert loaded.to_dict() == dataset.to_dict()
    assert loaded.images[0].capture_group == "g1"
    assert loaded.annotations[1].score == 0.5


def test_ensure_category_is_case_insensitive() -> None:
    dataset = make_dataset()
    category = dataset.ensure_category("SKRUV")
    assert category.id == 1
    new_category = dataset.ensure_category("bricka")
    assert new_category.id == 3
    assert dataset.next_category_id() == 4


def test_validate_rejects_broken_references() -> None:
    dataset = make_dataset()
    dataset.annotations[0].image_id = 99
    with pytest.raises(ValueError):
        dataset.validate()
