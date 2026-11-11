"""Enhetstester för datasetlagringen: spara, radera, grupper och metadata."""

import json

import numpy as np

from xray_detector.application.dataset_service import DatasetService
from xray_detector.domain.dataset import AnnotatedImage


def make_service(tmp_path) -> DatasetService:
    return DatasetService(tmp_path / "datasets", ["kniv", "pistol"])


def sample(fill: int = 100, class_name: str = "kniv") -> AnnotatedImage:
    frame = np.full((40, 50, 3), fill, dtype=np.uint8)
    return AnnotatedImage(frame, [{"class_name": class_name, "bbox": [2, 3, 10, 12]}])


def test_add_samples_creates_images_and_annotations(tmp_path):
    svc = make_service(tmp_path)
    svc.add_samples([sample(), sample(200, "pistol")])

    coco = svc.load_coco()
    assert len(coco["images"]) == 2
    assert len(coco["annotations"]) == 2
    assert (svc.images_dir / "img_000001.png").exists()
    assert (svc.images_dir / "img_000002.png").exists()


def test_capture_group_saved_for_simultaneous_samples(tmp_path):
    svc = make_service(tmp_path)
    svc.add_samples([sample(), sample(200)])
    svc.add_samples([sample(50)])

    images = svc.load_coco()["images"]
    groups = [image.get("group") for image in images]
    assert groups[0] == groups[1] == 1
    assert groups[2] == 2


def test_metadata_counts(tmp_path):
    svc = make_service(tmp_path)
    svc.add_samples([sample(), sample(200, "pistol")])
    info = svc.metadata()
    assert info["num_images"] == 2
    assert info["num_objects"] == 2
    assert info["updated"]


def test_newest_version_dir_is_migrated_to_the_root(tmp_path):
    """Ett dataset som sparades som v<N> flyttas upp när versionerna tas bort."""
    root = tmp_path / "datasets"
    old = root / "v1"
    (old / "images").mkdir(parents=True)
    (old / "images" / "img_000001.png").write_bytes(b"bild")
    (old / "dataset.json").write_text(
        json.dumps({"images": [{"id": 1, "file_name": "img_000001.png"}]}),
        encoding="utf-8",
    )

    svc = DatasetService(root, ["kniv"])

    assert (root / "dataset.json").exists()
    assert (svc.images_dir / "img_000001.png").exists()
    assert not old.exists()


def test_delete_images_removes_entries_and_files(tmp_path):
    svc = make_service(tmp_path)
    svc.add_samples([sample(), sample(200, "pistol")])
    before = svc.load_coco()
    victim = before["images"][1]["id"]

    svc.delete_images([victim])

    after = svc.load_coco()
    assert [image["id"] for image in after["images"]] == [before["images"][0]["id"]]
    assert all(annotation["image_id"] != victim for annotation in after["annotations"])
    assert not (svc.images_dir / "img_000002.png").exists()


def test_delete_images_is_noop_for_unknown_ids(tmp_path):
    svc = make_service(tmp_path)
    svc.add_samples([sample()])
    svc.delete_images([999])
    assert len(svc.load_coco()["images"]) == 1
