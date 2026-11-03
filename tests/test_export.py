from __future__ import annotations

from xray_detector.dataset.coco import read_coco
from xray_detector.dataset.export import export_dataset
from xray_detector.models import Detection


def test_export_writes_coco_yolo_and_manifest(paths, store, capture_factory) -> None:
    store.add_capture(
        capture_factory(0),
        {
            "left": [
                Detection(10, 10, 40, 50, 0, "skruv"),
                Detection(50, 10, 90, 40, 1, "mutter"),
            ],
            "right": [Detection(5, 5, 20, 20, 0, "skruv")],
        },
    )
    result = export_dataset(store, paths.exports, formats=("coco", "yolo"))
    manifest = result.manifest
    assert manifest["version"] == "1.0.1"
    assert manifest["image_count"] == 2
    assert manifest["annotation_count"] == 3
    assert manifest["object_count"] == 3
    assert manifest["categories"] == ["mutter", "skruv"]

    exported = read_coco(result.directory / "annotations.json")
    assert len(exported.images) == 2
    assert all(image.file_name.startswith("images/") for image in exported.images)
    assert (result.directory / "data.yaml").exists()
    labels = sorted((result.directory / "labels").glob("*.txt"))
    assert len(labels) == 2
    total_lines = sum(len(line.splitlines()) for line in (p.read_text() for p in labels))
    assert total_lines == 3
    assert (result.directory / "manifest.json").exists()

    _, metadata = store.load()
    assert metadata.version == "1.0.1"
    assert metadata.revision == 0


def test_export_without_freeze_keeps_version(paths, store, capture_factory) -> None:
    store.add_capture(capture_factory(0), {"left": [], "right": []})
    result = export_dataset(store, paths.exports, formats=("coco",), freeze_version=False)
    assert result.manifest["version"] == "1.0.0"
    _, metadata = store.load()
    assert metadata.version == "1.0.0"
    assert metadata.revision == 1
