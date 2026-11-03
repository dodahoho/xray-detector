from __future__ import annotations

from xray_detector.dataset.store import DatasetStore
from xray_detector.models import Detection


def test_add_capture_updates_dataset_and_metadata(capture_factory, store) -> None:
    capture = capture_factory(0)
    images, objects = store.add_capture(
        capture,
        {
            "left": [
                Detection(10, 10, 40, 50, 0, "skruv", 0.9),
                Detection(50, 10, 90, 40, 1, "mutter", 0.8),
            ],
            "right": [Detection(5, 5, 20, 20, 0, "skruv", 0.95)],
        },
    )
    assert (images, objects) == (2, 3)
    dataset, metadata = store.load()
    assert len(dataset.images) == 2
    assert len(dataset.annotations) == 3
    assert metadata.revision == 1
    assert metadata.image_count == 2
    assert metadata.annotation_count == 3
    assert metadata.categories == ["mutter", "skruv"]
    assert all(store.image_path(image).exists() for image in dataset.images)
    assert {image.capture_group for image in dataset.images} == {capture.group_id}
    first_annotation = dataset.annotations[0]
    assert first_annotation.bbox == [10, 10, 30, 40]
    assert first_annotation.area == 1200


def test_categories_are_reused_across_captures(capture_factory, store) -> None:
    store.add_capture(
        capture_factory(0),
        {"left": [Detection(1, 1, 10, 10, 0, "Skruv")], "right": []},
    )
    store.add_capture(
        capture_factory(1),
        {"left": [Detection(1, 1, 10, 10, 0, "skruv")], "right": []},
    )
    dataset, _ = store.load()
    assert len(dataset.categories) == 1


def test_freeze_version_bumps_patch(capture_factory, store) -> None:
    store.add_capture(capture_factory(0), {"left": [], "right": []})
    metadata = store.freeze_version()
    assert metadata.version == "1.0.1"
    assert metadata.revision == 0
    dataset, loaded = store.load()
    assert len(dataset.images) == 2
    assert loaded.version == "1.0.1"


def test_create_existing_dataset_fails(store) -> None:
    import pytest

    with pytest.raises(FileExistsError):
        store.create()
