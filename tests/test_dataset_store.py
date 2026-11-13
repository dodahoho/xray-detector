"""Enhetstester för datasetlagringen: spara, radera, grupper och metadata."""

import json

import numpy as np

from xray_detector.application.dataset_service import DatasetService
from xray_detector.domain.dataset import AnnotatedImage


def make_service(tmp_path) -> DatasetService:
    return DatasetService(tmp_path / "datasets")


def sample(fill: int = 100, class_name: str = "kniv") -> AnnotatedImage:
    frame = np.full((40, 50, 3), fill, dtype=np.uint8)
    return AnnotatedImage(frame, [{"class_name": class_name, "bbox": [2, 3, 10, 12]}])


def test_add_samples_writes_images_labels_and_classes(tmp_path):
    svc = make_service(tmp_path)
    svc.add_samples([sample(), sample(200, "pistol")])

    dataset = svc.load_dataset()
    assert len(dataset["images"]) == 2
    assert dataset["classes"] == ["kniv", "pistol"]
    assert (svc.images_dir / "img_000001.png").exists()
    assert (svc.images_dir / "img_000002.png").exists()
    labels = svc.store.labels_dir
    assert (labels / "img_000001.txt").read_text(encoding="utf-8").startswith("0 ")
    assert (labels / "img_000002.txt").read_text(encoding="utf-8").startswith("1 ")
    assert 'names: ["kniv", "pistol"]' in svc.store.data_yaml.read_text(encoding="utf-8")


def test_label_is_normalised_to_the_image_size(tmp_path):
    """YOLO lagrar måtten normaliserade mot bildens bredd och höjd (TASK-78)."""
    svc = make_service(tmp_path)
    svc.add_samples([sample()])

    row = (svc.store.labels_dir / "img_000001.txt").read_text(encoding="utf-8").split()
    assert [round(float(value), 6) for value in row[1:]] == [0.14, 0.225, 0.2, 0.3]


def test_capture_group_saved_for_simultaneous_samples(tmp_path):
    svc = make_service(tmp_path)
    svc.add_samples([sample(), sample(200)])
    svc.add_samples([sample(50)])

    images = svc.load_dataset()["images"]
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

    svc = DatasetService(root)

    assert (root / "dataset.json").exists()
    assert (svc.images_dir / "img_000001.png").exists()
    assert not old.exists()


def test_coco_dataset_is_migrated_to_yolo(tmp_path):
    """Ett dataset som sparades som COCO konverteras till YOLO vid start (TASK-78)."""
    root = tmp_path / "datasets"
    (root / "images").mkdir(parents=True)
    (root / "images" / "img_000001.png").write_bytes(b"bild")
    (root / "dataset.json").write_text(
        json.dumps(
            {
                "info": {"created": "x", "updated": "y", "num_images": 1, "num_objects": 1},
                "categories": [{"id": 1, "name": "kniv"}],
                "images": [
                    {
                        "id": 1,
                        "file_name": "img_000001.png",
                        "width": 50,
                        "height": 40,
                        "group": 1,
                    }
                ],
                "annotations": [
                    {"id": 1, "image_id": 1, "category_id": 1, "bbox": [2, 3, 10, 12]}
                ],
            }
        ),
        encoding="utf-8",
    )

    svc = DatasetService(root)

    assert svc.classes() == ["kniv"]
    label = (root / "labels" / "img_000001.txt").read_text(encoding="utf-8")
    assert label.startswith("0 ")
    metadata = json.loads((root / "dataset.json").read_text(encoding="utf-8"))
    assert "annotations" not in metadata and "categories" not in metadata
    annotations = svc.load_dataset()["images"][0]["annotations"]
    assert [annotation["class_name"] for annotation in annotations] == ["kniv"]


def test_delete_images_removes_entries_files_and_labels(tmp_path):
    svc = make_service(tmp_path)
    svc.add_samples([sample(), sample(200, "pistol")])
    before = svc.load_dataset()
    victim = before["images"][1]["id"]

    svc.delete_images([victim])

    after = svc.load_dataset()
    assert [image["id"] for image in after["images"]] == [before["images"][0]["id"]]
    assert not (svc.images_dir / "img_000002.png").exists()
    assert not (svc.store.labels_dir / "img_000002.txt").exists()
    assert svc.metadata()["num_objects"] == 1


def test_delete_images_is_noop_for_unknown_ids(tmp_path):
    svc = make_service(tmp_path)
    svc.add_samples([sample()])
    svc.delete_images([999])
    assert len(svc.load_dataset()["images"]) == 1
