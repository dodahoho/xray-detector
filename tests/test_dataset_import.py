"""Enhetstester för import av ett YOLO-dataset (TASK-159)."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from xray_detector.domain.dataset import MODE_ALL, AnnotatedImage, VariationSettings, capture_group
from xray_detector.infrastructure.dataset_store.export import export_yolo
from xray_detector.infrastructure.dataset_store.import_dataset import (
    MODE_EXTEND,
    MODE_REPLACE,
    import_yolo,
)
from xray_detector.infrastructure.dataset_store.store import DatasetStore
from xray_detector.infrastructure.dataset_store.yolo import (
    label_name,
    write_data_yaml,
    write_labels,
)


def sample(fill: int = 100, class_name: str = "kniv") -> AnnotatedImage:
    frame = np.full((40, 50, 3), fill, dtype=np.uint8)
    return AnnotatedImage(frame, [{"class_name": class_name, "bbox": [2, 3, 10, 12]}])


def add_pairs(store: DatasetStore, pairs: int, per_pair: int = 2) -> None:
    for index in range(pairs):
        store.add_samples([sample(40 + index * 20) for _ in range(per_pair)])


def plain_dataset(root: Path, names: list[str], images: dict[str, list[tuple]]) -> Path:
    """Skriver ett YOLO-dataset utan appens dataset.json, som ett externt dataset."""
    (root / "images").mkdir(parents=True)
    (root / "labels").mkdir(parents=True)
    for file_name, rows in images.items():
        cv2.imwrite(str(root / "images" / file_name), np.full((40, 50, 3), 90, np.uint8))
        write_labels(root / "labels" / label_name(file_name), rows)
    write_data_yaml(root / "data.yaml", names)
    return root / "data.yaml"


def test_export_import_round_trip_restores_the_dataset(tmp_path):
    """Kedjan export -> import ger tillbaka datasetet som det var före exporten (TASK-159)."""
    source = DatasetStore(tmp_path / "source")
    add_pairs(source, 3)
    source.add_variations(
        VariationSettings(count=1, mode=MODE_ALL, rotation=True, rotation_degrees=10),
        seed=1,
    )
    before = source.load_dataset()
    data_yaml = export_yolo(source, tmp_path / "exports")

    target = DatasetStore(tmp_path / "target")
    result = import_yolo(target, data_yaml, MODE_REPLACE)

    after = target.load_dataset()
    assert result.images == len(before["images"])
    assert result.pairs == len({capture_group(image) for image in before["images"]})
    assert result.skipped == 0
    assert after["classes"] == before["classes"]
    assert [image["file_name"] for image in after["images"]] == [
        image["file_name"] for image in before["images"]
    ]
    for expected, actual in zip(before["images"], after["images"], strict=True):
        assert actual["id"] == expected["id"]
        assert actual["group"] == expected["group"]
        assert actual["captured"] == expected["captured"]
        assert actual.get("synthetic") == expected.get("synthetic")
        assert actual.get("source") == expected.get("source")
        assert actual.get("variation") == expected.get("variation")
        assert [ann["class_name"] for ann in actual["annotations"]] == [
            ann["class_name"] for ann in expected["annotations"]
        ]
        for expected_ann, actual_ann in zip(
            expected["annotations"], actual["annotations"], strict=True
        ):
            assert actual_ann["bbox"] == pytest.approx(expected_ann["bbox"], abs=1e-3)


def test_import_without_metadata_gives_one_pair_per_image(tmp_path):
    """Ett externt dataset saknar bildpar, så varje bild blir ett eget par (TASK-159)."""
    data_yaml = plain_dataset(
        tmp_path / "external",
        ["kniv", "pistol"],
        {"a.png": [(1, 0.5, 0.5, 0.2, 0.2)], "b.png": [(0, 0.4, 0.4, 0.1, 0.1)]},
    )
    store = DatasetStore(tmp_path / "datasets")

    result = import_yolo(store, data_yaml)

    dataset = store.load_dataset()
    assert result.images == 2
    assert result.pairs == 2
    assert dataset["classes"] == ["kniv", "pistol"]
    assert [image["file_name"] for image in dataset["images"]] == ["a.png", "b.png"]
    assert [image["group"] for image in dataset["images"]] == [1, 2]
    assert [ann["class_name"] for ann in dataset["images"][0]["annotations"]] == ["pistol"]
    assert dataset["images"][0]["width"] == 50
    assert dataset["images"][0]["height"] == 40
    assert dataset["images"][0]["captured"]


def test_extend_keeps_the_existing_images_and_appends_classes(tmp_path):
    """Utökning behåller datasetet och lägger nya klasser sist (TASK-159)."""
    store = DatasetStore(tmp_path / "datasets")
    store.add_samples([sample(class_name="kniv")])
    data_yaml = plain_dataset(
        tmp_path / "external", ["pistol"], {"a.png": [(0, 0.5, 0.5, 0.2, 0.2)]}
    )

    result = import_yolo(store, data_yaml, MODE_EXTEND)

    dataset = store.load_dataset()
    assert result.images == 1
    assert dataset["classes"] == ["kniv", "pistol"]
    existing, imported = dataset["images"]
    assert existing["file_name"] == "img_000001.png"
    assert imported["id"] == 2
    assert imported["group"] == 2
    assert imported["file_name"] == "img_000002.png"
    assert imported["annotations"][0]["class_name"] == "pistol"
    # den befintliga annoteringen behåller sitt index när klassen läggs sist
    assert (store.labels_dir / "img_000001.txt").read_text(encoding="utf-8").startswith("0 ")
    assert (store.labels_dir / "img_000002.txt").read_text(encoding="utf-8").startswith("1 ")


def test_replace_removes_the_existing_images(tmp_path):
    """Ersättning tömmer datasetet innan importen skriver dit bilderna (TASK-159)."""
    store = DatasetStore(tmp_path / "datasets")
    store.add_samples([sample(), sample()])
    data_yaml = plain_dataset(tmp_path / "external", ["pistol"], {"a.png": []})

    import_yolo(store, data_yaml, MODE_REPLACE)

    dataset = store.load_dataset()
    assert [image["file_name"] for image in dataset["images"]] == ["a.png"]
    assert dataset["classes"] == ["pistol"]
    assert sorted(path.name for path in store.images_dir.glob("*.png")) == ["a.png"]
    assert sorted(path.name for path in store.labels_dir.glob("*.txt")) == ["a.txt"]


def test_import_reads_a_split_layout(tmp_path):
    """Ett dataset med train/images och train/labels läses också (TASK-159)."""
    root = tmp_path / "external"
    (root / "train" / "images").mkdir(parents=True)
    (root / "train" / "labels").mkdir(parents=True)
    cv2.imwrite(
        str(root / "train" / "images" / "x.png"), np.full((20, 30, 3), 70, np.uint8)
    )
    write_labels(root / "train" / "labels" / "x.txt", [(0, 0.5, 0.5, 0.2, 0.2)])
    write_data_yaml(root / "data.yaml", ["kniv"], "train/images", "train/images")

    store = DatasetStore(tmp_path / "datasets")
    result = import_yolo(store, root / "data.yaml")

    assert result.images == 1
    assert store.load_dataset()["images"][0]["annotations"][0]["class_name"] == "kniv"


def test_extend_moves_the_synthetic_link_to_the_new_ids(tmp_path):
    """En variation pekar på originalets nya id när importen utökar (TASK-159)."""
    source = DatasetStore(tmp_path / "source")
    add_pairs(source, 2)
    source.add_variations(
        VariationSettings(count=1, mode=MODE_ALL, rotation=True, rotation_degrees=10),
        seed=1,
    )
    data_yaml = export_yolo(source, tmp_path / "exports")

    target = DatasetStore(tmp_path / "target")
    target.add_samples([sample()])
    import_yolo(target, data_yaml, MODE_EXTEND)

    images = target.load_dataset()["images"]
    by_id = {image["id"]: image for image in images}
    synthetic = [image for image in images if image.get("synthetic")]
    assert synthetic
    for image in synthetic:
        assert image["source"] in by_id
        assert not by_id[image["source"]].get("synthetic")


def test_extend_does_not_overwrite_an_existing_file(tmp_path):
    """Utökning döper om importens bilder, så en befintlig fil aldrig skrivs över (TASK-159)."""
    store = DatasetStore(tmp_path / "datasets")
    store.add_samples([sample()])
    data_yaml = plain_dataset(
        tmp_path / "external", ["kniv"], {"img_000001.png": [(0, 0.5, 0.5, 0.2, 0.2)]}
    )

    import_yolo(store, data_yaml, MODE_EXTEND)

    assert sorted(path.name for path in store.images_dir.glob("*.png")) == [
        "img_000001.png",
        "img_000002.png",
    ]
    assert len(store.load_dataset()["images"]) == 2


def test_import_skips_files_that_are_not_images(tmp_path):
    """En fil som inte går att läsa hoppas över i stället för att avbryta importen (TASK-159)."""
    root = tmp_path / "external"
    (root / "images").mkdir(parents=True)
    (root / "images" / "broken.png").write_text("inte en bild", encoding="utf-8")
    cv2.imwrite(str(root / "images" / "ok.png"), np.full((20, 30, 3), 70, np.uint8))
    write_data_yaml(root / "data.yaml", ["kniv"])

    result = import_yolo(DatasetStore(tmp_path / "datasets"), root / "data.yaml")

    assert result.images == 1
    assert result.skipped == 1


def test_import_rejects_a_dataset_without_classes(tmp_path):
    root = tmp_path / "external"
    (root / "images").mkdir(parents=True)
    cv2.imwrite(str(root / "images" / "a.png"), np.full((20, 30, 3), 70, np.uint8))
    (root / "data.yaml").write_text("train: images\n", encoding="utf-8")

    with pytest.raises(ValueError, match="klasslista"):
        import_yolo(DatasetStore(tmp_path / "datasets"), root / "data.yaml")


def test_import_rejects_a_dataset_without_images(tmp_path):
    root = tmp_path / "external"
    root.mkdir()
    write_data_yaml(root / "data.yaml", ["kniv"])

    with pytest.raises(ValueError, match="inga bilder"):
        import_yolo(DatasetStore(tmp_path / "datasets"), root / "data.yaml")


def test_import_rejects_an_unknown_mode(tmp_path):
    data_yaml = plain_dataset(tmp_path / "external", ["kniv"], {"a.png": []})

    with pytest.raises(ValueError, match="okänt läge"):
        import_yolo(DatasetStore(tmp_path / "datasets"), data_yaml, "merge")
