"""Enhetstester för datasetlagringen: spara, radera, grupper och metadata."""

import json
import logging

import numpy as np

from xray_detector.domain.dataset import MODE_ALL, AnnotatedImage, VariationSettings
from xray_detector.infrastructure.dataset_store.export import (
    group_count,
)
from xray_detector.infrastructure.dataset_store.store import DatasetStore


def make_service(tmp_path) -> DatasetStore:
    return DatasetStore(tmp_path / "datasets")


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
    labels = svc.labels_dir
    assert (labels / "img_000001.txt").read_text(encoding="utf-8").startswith("0 ")
    assert (labels / "img_000002.txt").read_text(encoding="utf-8").startswith("1 ")
    assert 'names: ["kniv", "pistol"]' in svc.data_yaml.read_text(encoding="utf-8")


def test_label_is_normalised_to_the_image_size(tmp_path):
    """YOLO lagrar måtten normaliserade mot bildens bredd och höjd (TASK-78)."""
    svc = make_service(tmp_path)
    svc.add_samples([sample()])

    row = (svc.labels_dir / "img_000001.txt").read_text(encoding="utf-8").split()
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


def test_delete_images_removes_entries_files_and_labels(tmp_path):
    svc = make_service(tmp_path)
    svc.add_samples([sample(), sample(200, "pistol")])
    before = svc.load_dataset()
    victim = before["images"][1]["id"]

    svc.delete_images([victim])

    after = svc.load_dataset()
    assert [image["id"] for image in after["images"]] == [before["images"][0]["id"]]
    assert not (svc.images_dir / "img_000002.png").exists()
    assert not (svc.labels_dir / "img_000002.txt").exists()
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
    assert (svc.labels_dir / "img_000001.txt").read_text(
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
    svc.metadata_path.write_text("{ inte json", encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="xray"):
        dataset = svc.load_dataset()

    assert dataset["images"] == []
    assert dataset["info"]["num_images"] == 0
    assert "dataset.json går inte att läsa" in caplog.text


def test_metadata_without_images_is_treated_as_broken(tmp_path, caplog):
    """Giltig JSON med fel form ska ge tomt dataset i stället för KeyError (TASK-124)."""
    svc = make_service(tmp_path)
    svc.metadata_path.write_text('{"info": {}}', encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="xray"):
        dataset = svc.load_dataset()

    assert dataset["images"] == []
    assert "saknar info eller images" in caplog.text


def test_broken_metadata_is_replaced_by_the_next_save(tmp_path):
    """Nästa skrivning ska ersätta den trasiga filen i stället för att lägga till (TASK-124)."""
    svc = make_service(tmp_path)
    svc.metadata_path.write_text("{ inte json", encoding="utf-8")

    svc.add_samples([sample()])

    dataset = svc.load_dataset()
    assert len(dataset["images"]) == 1
    assert dataset["info"]["num_images"] == 1


def _label_rows(svc) -> int:
    """Antal annoteringar som faktiskt ligger i labels/."""
    return sum(
        len(path.read_text(encoding="utf-8").splitlines())
        for path in svc.labels_dir.glob("*.txt")
    )


def test_num_objects_is_counted_from_the_label_files(tmp_path):
    """num_objects räknas i _save_metadata och följer labels/ genom alla operationer (TASK-126)."""
    svc = make_service(tmp_path)
    svc.add_samples([sample(), sample(200, "pistol")])
    assert svc.metadata()["num_objects"] == _label_rows(svc) == 2

    first = svc.load_dataset()["images"][0]
    svc.replace_samples(
        [first["id"]],
        [
            AnnotatedImage(
                np.full((40, 50, 3), 90, dtype=np.uint8),
                [
                    {"class_name": "kniv", "bbox": [2, 3, 10, 12]},
                    {"class_name": "kniv", "bbox": [12, 3, 20, 12]},
                    {"class_name": "pistol", "bbox": [22, 3, 30, 12]},
                ],
            )
        ],
    )
    assert svc.metadata()["num_objects"] == _label_rows(svc) == 4

    svc.add_variations(VariationSettings(count=1, mode=MODE_ALL, flip_horizontal=True))
    assert svc.metadata()["num_objects"] == _label_rows(svc)
    assert svc.metadata()["num_objects"] > 4

    svc.delete_images([first["id"]])
    assert svc.metadata()["num_objects"] == _label_rows(svc)


def test_num_objects_ignores_a_stale_stored_value(tmp_path):
    """Ett gammalt värde i dataset.json skrivs över av det räknade (TASK-126)."""
    svc = make_service(tmp_path)
    svc.add_samples([sample()])
    metadata = json.loads(svc.metadata_path.read_text(encoding="utf-8"))
    metadata["info"]["num_objects"] = 99
    svc.metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    svc.add_samples([sample(200)])

    assert svc.metadata()["num_objects"] == 2


def test_data_yaml_with_a_multiline_names_dict_is_read(tmp_path):
    """Ultralytics dictform över flera rader läses med yaml.safe_load (TASK-136)."""
    from xray_detector.infrastructure.dataset_store.yolo import read_classes

    path = tmp_path / "data.yaml"
    path.write_text(
        """path: /data
train: images
val: images
nc: 3
names:
  0: kniv
  1: pistol   # vanligast
  2: 'cigaretter'
""",
        encoding="utf-8",
    )

    assert read_classes(path) == ["kniv", "pistol", "cigaretter"]


def test_data_yaml_with_a_list_of_names_is_read(tmp_path):
    """Listformen, som write_data_yaml skriver, läses tillbaka (TASK-136)."""
    from xray_detector.infrastructure.dataset_store.yolo import read_classes, write_data_yaml

    path = tmp_path / "data.yaml"
    write_data_yaml(path, ["kniv", "pistol"])

    assert read_classes(path) == ["kniv", "pistol"]


def test_a_broken_data_yaml_gives_no_classes(tmp_path):
    """En trasig data.yaml ger en tom klasslista i stället för ett undantag (TASK-136)."""
    from xray_detector.infrastructure.dataset_store.yolo import read_classes

    path = tmp_path / "data.yaml"
    path.write_text("names: [oterminerad\n", encoding="utf-8")

    assert read_classes(path) == []


def test_capture_grouping_is_shared_by_every_reader(tmp_path):
    """Samma gruppering används av lagring, export, utvärdering och vy (TASK-137)."""
    from xray_detector.application.evaluation import view_labels
    from xray_detector.domain.dataset import capture_group, group_images

    images = [
        {"id": 1, "group": 7, "annotations": []},
        {"id": 2, "group": 7, "annotations": []},
        {"id": 3, "group": 8, "annotations": []},
        # en variation hör till sin ursprungsbilds grupp, inte sin egen
        {"id": 4, "group": 9, "synthetic": True, "source": 1, "annotations": []},
    ]

    assert capture_group(images[0]) == 7
    assert capture_group({"id": 5}) == 5
    assert group_count(images) == 2
    assert set(group_images(images)) == {7, 8}
    # variationen blir tredje vyn i ursprungsgruppen, inte en egen grupp
    assert view_labels(images)[4] == "vy 3"
