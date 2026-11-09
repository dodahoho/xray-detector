"""Enhetstester för datasetlagringen: spara, radera, grupper och metadata."""

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
    svc.add_samples(1, [sample(), sample(200, "pistol")])

    coco = svc.load_coco(1)
    assert len(coco["images"]) == 2
    assert len(coco["annotations"]) == 2
    assert svc.versions() == [1]
    assert (svc.version_dir(1) / "images" / "img_000001.png").exists()
    assert (svc.version_dir(1) / "images" / "img_000002.png").exists()


def test_capture_group_saved_for_simultaneous_samples(tmp_path):
    svc = make_service(tmp_path)
    svc.add_samples(1, [sample(), sample(200)])
    svc.add_samples(1, [sample(50)])

    images = svc.load_coco(1)["images"]
    groups = [image.get("group") for image in images]
    assert groups[0] == groups[1] == 1
    assert groups[2] == 2


def test_metadata_counts(tmp_path):
    svc = make_service(tmp_path)
    svc.add_samples(1, [sample(), sample(200, "pistol")])
    info = svc.metadata(1)
    assert info["num_images"] == 2
    assert info["num_objects"] == 2
    assert info["updated"]


def test_current_and_new_version(tmp_path):
    svc = make_service(tmp_path)
    assert svc.current_version() == 0
    assert svc.new_version() == 1
    svc.add_samples(1, [sample()])
    svc.add_samples(2, [sample()])
    assert svc.current_version() == 2
    assert svc.versions() == [1, 2]


def test_delete_images_removes_entries_and_files(tmp_path):
    svc = make_service(tmp_path)
    svc.add_samples(1, [sample(), sample(200, "pistol")])
    before = svc.load_coco(1)
    victim = before["images"][1]["id"]

    svc.delete_images(1, [victim])

    after = svc.load_coco(1)
    assert [image["id"] for image in after["images"]] == [before["images"][0]["id"]]
    assert all(annotation["image_id"] != victim for annotation in after["annotations"])
    assert not (svc.version_dir(1) / "images" / "img_000002.png").exists()


def test_delete_images_is_noop_for_unknown_ids(tmp_path):
    svc = make_service(tmp_path)
    svc.add_samples(1, [sample()])
    svc.delete_images(1, [999])
    assert len(svc.load_coco(1)["images"]) == 1
