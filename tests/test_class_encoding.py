"""Klassnamn med nationella tecken (TASK-165).

Ett namn som sparats som UTF-8 men lästs som latin-1 blir mojibake: "löpare"
blir "lÃ¶pare". Namnet kan hamna i datasetets data.yaml, i exporten och i
modellens vikter, och då visar klassmärket fel tecken. Läsarna rättar därför
namnet, så hela kedjan dataset -> träning -> detektion får samma tecken.
"""

from xray_detector.domain.dataset import repair_mojibake
from xray_detector.infrastructure.dataset_store.store import DatasetStore
from xray_detector.infrastructure.dataset_store.yolo import read_classes, write_data_yaml
from xray_detector.infrastructure.detectors.base import class_names_from

MOJIBAKE = "lÃ¶pare"
CORRECT = "löpare"


def test_mojibake_is_repaired():
    assert repair_mojibake(MOJIBAKE) == CORRECT


def test_a_correct_name_is_left_alone():
    assert repair_mojibake(CORRECT) == CORRECT


def test_an_ascii_name_is_left_alone():
    assert repair_mojibake("zipper") == "zipper"


def test_an_empty_name_is_left_alone():
    assert repair_mojibake("") == ""


def test_a_name_outside_latin_1_is_left_alone():
    """Tecken som inte går att koda som latin-1 kan inte vara mojibake."""
    assert repair_mojibake("kniv-日本") == "kniv-日本"


def test_read_classes_repairs_a_mojibake_name(tmp_path):
    path = tmp_path / "data.yaml"
    path.write_text(
        f'path: {tmp_path}\n'
        "train: images\n"
        "val: images\n"
        "nc: 1\n"
        f'names: ["{MOJIBAKE}"]\n',
        encoding="utf-8",
    )

    assert read_classes(path) == [CORRECT]


def test_read_classes_repairs_a_mojibake_name_in_the_dict_form(tmp_path):
    path = tmp_path / "data.yaml"
    path.write_text(
        f"path: {tmp_path}\n"
        "train: images\n"
        "val: images\n"
        "nc: 1\n"
        "names:\n"
        f"  0: {MOJIBAKE}\n",
        encoding="utf-8",
    )

    assert read_classes(path) == [CORRECT]


def test_write_data_yaml_repairs_the_name(tmp_path):
    path = tmp_path / "data.yaml"

    write_data_yaml(path, [MOJIBAKE])

    assert read_classes(path) == [CORRECT]
    assert MOJIBAKE not in path.read_text(encoding="utf-8")


def test_the_store_repairs_the_name_when_it_is_written(tmp_path):
    store = DatasetStore(tmp_path / "datasets")

    store.set_classes([MOJIBAKE])

    assert store.classes() == [CORRECT]


def test_class_names_from_repairs_a_mojibake_name():
    assert class_names_from({0: MOJIBAKE}, "vikter.pt") == [CORRECT]


def test_class_names_from_repairs_a_mojibake_name_in_a_list():
    assert class_names_from([MOJIBAKE, "zipper"], "vikter.pth") == [CORRECT, "zipper"]
