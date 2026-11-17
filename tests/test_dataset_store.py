"""Enhetstester för datasetlagringen: spara, radera, grupper och metadata."""

import json
import logging

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


# --- Oanvända klasser (TASK-109) ---


def test_unused_classes_are_the_ones_without_annotations(tmp_path):
    svc = make_service(tmp_path)
    svc.set_classes(["kniv", "pistol", "cannabis"])
    svc.add_samples([sample(class_name="pistol")])

    assert svc.unused_classes() == ["kniv", "cannabis"]


def test_remove_unused_classes_keeps_the_annotations_of_the_used_ones(tmp_path):
    """Indexen skrivs om, så en kvarvarande klass behåller sina annoteringar."""
    svc = make_service(tmp_path)
    svc.set_classes(["kniv", "pistol", "cannabis"])
    svc.add_samples([sample(class_name="pistol")])

    removed = svc.remove_unused_classes()

    assert removed == ["kniv", "cannabis"]
    assert svc.classes() == ["pistol"]
    dataset = svc.load_dataset()
    assert [a["class_name"] for a in dataset["images"][0]["annotations"]] == ["pistol"]
    assert (svc.store.labels_dir / "img_000001.txt").read_text(
        encoding="utf-8"
    ).startswith("0 ")


def test_remove_unused_classes_is_a_no_op_when_every_class_is_used(tmp_path):
    svc = make_service(tmp_path)
    svc.add_samples([sample(), sample(200, "pistol")])

    assert svc.remove_unused_classes() == []
    assert svc.classes() == ["kniv", "pistol"]


def test_every_class_is_unused_before_anything_is_annotated(tmp_path):
    svc = make_service(tmp_path)
    svc.set_classes(["kniv", "pistol"])

    assert svc.unused_classes() == ["kniv", "pistol"]


# --- Redigering ersätter bilden på plats (TASK-110) ---


def test_replace_samples_keeps_the_id_and_rewrites_the_annotations(tmp_path):
    svc = make_service(tmp_path)
    svc.add_samples([sample(), sample(200)])
    before = svc.load_dataset()["images"][0]

    svc.replace_samples(
        [before["id"]],
        [AnnotatedImage(np.full((40, 50, 3), 90, np.uint8),
                        [{"class_name": "pistol", "bbox": [4, 4, 8, 8]}])],
    )

    images = svc.load_dataset()["images"]
    assert len(images) == 1 + 1  # den andra bilden ligger kvar
    assert images[0]["id"] == before["id"]
    assert images[0]["group"] == before["group"]
    assert [a["class_name"] for a in images[0]["annotations"]] == ["pistol"]
    assert svc.metadata()["num_objects"] == 2


def test_replace_samples_keeps_the_synthetic_origin(tmp_path):
    """En redigerad variation fortsätter höra till sitt ursprung (TASK-110)."""
    from xray_detector.domain.dataset import VariationSettings

    svc = make_service(tmp_path)
    svc.add_samples([sample()])
    svc.add_variations(VariationSettings(count=1, flip_horizontal=True), seed=1)
    variation = next(i for i in svc.load_dataset()["images"] if i.get("synthetic"))

    svc.replace_samples([variation["id"]], [sample(150)])

    updated = next(i for i in svc.load_dataset()["images"] if i["id"] == variation["id"])
    assert updated["synthetic"] is True
    assert updated["source"] == variation["source"]


def test_replace_samples_falls_back_to_delete_and_add_on_a_count_mismatch(tmp_path):
    svc = make_service(tmp_path)
    svc.add_samples([sample(), sample(200)])
    ids = [image["id"] for image in svc.load_dataset()["images"]]

    svc.replace_samples(ids, [sample(90)])

    images = svc.load_dataset()["images"]
    assert len(images) == 1
    assert len(images[0]["annotations"]) == 1
    assert svc.metadata()["num_objects"] == 1


def test_broken_metadata_gives_an_empty_dataset_and_a_warning(tmp_path, caplog):
    """En trasig dataset.json ska inte krascha appen (TASK-124)."""
    svc = make_service(tmp_path)
    svc.store.metadata_path.write_text("{ inte json", encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="xray"):
        dataset = svc.load_dataset()

    assert dataset["images"] == []
    assert dataset["info"]["num_images"] == 0
    assert "dataset.json går inte att läsa" in caplog.text


def test_metadata_without_images_is_treated_as_broken(tmp_path, caplog):
    """Giltig JSON med fel form ska ge tomt dataset i stället för KeyError (TASK-124)."""
    svc = make_service(tmp_path)
    svc.store.metadata_path.write_text('{"info": {}}', encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="xray"):
        dataset = svc.load_dataset()

    assert dataset["images"] == []
    assert "saknar info eller images" in caplog.text


def test_broken_metadata_is_replaced_by_the_next_save(tmp_path):
    """Nästa skrivning ska ersätta den trasiga filen i stället för att lägga till (TASK-124)."""
    svc = make_service(tmp_path)
    svc.store.metadata_path.write_text("{ inte json", encoding="utf-8")

    svc.add_samples([sample()])

    dataset = svc.load_dataset()
    assert len(dataset["images"]) == 1
    assert dataset["info"]["num_images"] == 1
