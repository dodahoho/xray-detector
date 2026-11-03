from __future__ import annotations

import json

import numpy as np

from xray_detector.domain.annotation import AnnotationBox
from xray_detector.domain.detection import BBox
from xray_detector.infrastructure.dataset_store.coco_store import CocoStore


def _pair(frame: np.ndarray) -> dict[str, np.ndarray]:
    return {"cam0": frame.copy(), "cam1": frame.copy()}


def test_add_pair_creates_version(tmp_path, frame):
    store = CocoStore(tmp_path / "default", "default")
    annotations = {
        "cam0": [AnnotationBox(BBox(10, 10, 50, 50), "part")],
        "cam1": [AnnotationBox(BBox(20, 20, 60, 60), "part")],
    }

    summary = store.add_pair(_pair(frame), annotations, pair_id="pair001")

    assert summary.version == "v000001"
    assert summary.image_count == 2
    assert summary.pair_count == 1
    assert summary.annotation_count == 2
    assert summary.category_counts == {"part": 2}
    assert store.info().latest_version == "v000001"
    assert store.info().next_version == 2
    assert (store.versions_dir / "v000001.json").exists()

    coco = store.current_coco()
    assert len(coco["images"]) == 2
    assert {image["pair_id"] for image in coco["images"]} == {"pair001"}
    assert {image["camera_role"] for image in coco["images"]} == {"cam0", "cam1"}
    assert all((store.images_dir / image["file_name"]).exists() for image in coco["images"])


def test_versions_are_immutable_and_categories_reused(tmp_path, frame):
    store = CocoStore(tmp_path / "default", "default")
    store.add_pair(
        _pair(frame),
        {"cam0": [AnnotationBox(BBox(1, 1, 20, 20), "part")], "cam1": []},
    )
    first_category_id = store.current_coco()["categories"][0]["id"]

    store.add_pair(
        _pair(frame),
        {
            "cam0": [AnnotationBox(BBox(2, 2, 30, 30), "part")],
            "cam1": [AnnotationBox(BBox(3, 3, 40, 40), "defect")],
        },
    )

    coco = store.current_coco()
    assert len(coco["categories"]) == 2
    by_name = {category["name"]: category for category in coco["categories"]}
    assert by_name["part"]["id"] == first_category_id
    assert store.info().latest_version == "v000002"

    version1 = store.load_version("v000001")
    assert len(version1["images"]) == 2
    assert len(version1["annotations"]) == 1
    assert len(version1["categories"]) == 1
    assert store.load_version("v000002")["info"]["version"] == "v000002"


def test_version_manifest_contains_counts(tmp_path, frame):
    store = CocoStore(tmp_path / "default", "default")
    store.add_pair(
        _pair(frame),
        {
            "cam0": [AnnotationBox(BBox(10, 10, 50, 50), "a")],
            "cam1": [AnnotationBox(BBox(12, 12, 52, 52), "b")],
        },
    )
    manifest = store.version_manifest("v000001")
    assert manifest["image_count"] == 2
    assert manifest["pair_count"] == 1
    assert manifest["annotation_count"] == 2
    assert manifest["category_counts"] == {"a": 1, "b": 1}
    assert len(manifest["coco_sha256"]) == 64

    on_disk = json.loads((store.versions_dir / "v000001.json").read_text(encoding="utf-8"))
    assert on_disk["manifest"] == manifest


def test_invalid_frame_rejected(tmp_path):
    store = CocoStore(tmp_path / "default", "default")
    try:
        store.add_pair({"cam0": np.zeros((10, 10, 3), dtype=np.uint8)}, {})
    except ValueError as exc:
        assert "cam0 and cam1" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_manual_annotations_omit_score_and_respect_min_size(tmp_path, frame):
    store = CocoStore(tmp_path / "default", "default")
    store.add_pair(
        _pair(frame),
        {
            "cam0": [
                AnnotationBox(BBox(10, 10, 50, 50), "part"),
                AnnotationBox(BBox(10, 10, 13, 13), "too-small"),
            ],
            "cam1": [],
        },
        min_box_size=5,
    )
    coco = store.current_coco()
    assert len(coco["annotations"]) == 1
    assert "score" not in coco["annotations"][0]
    assert {category["name"] for category in coco["categories"]} == {"part"}
