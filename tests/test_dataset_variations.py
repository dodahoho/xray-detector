"""Syntetiska bildvariationer: transformerna och datasetlagringen (TASK-88)."""

import random

import numpy as np
import pytest

from xray_detector.application.dataset_service import DatasetService
from xray_detector.domain.dataset import (
    MODE_ALL,
    MODE_PER_TYPE,
    MODE_RANDOM,
    AnnotatedImage,
    VariationSettings,
)
from xray_detector.infrastructure.dataset_store.augment import (
    adjust_color,
    apply_variation,
    apply_variations,
    describe,
    flip,
    rotate,
    scale,
    variation_plan,
)

WIDTH = 50
HEIGHT = 40
BBOX = [2, 3, 10, 12]


def _frame() -> np.ndarray:
    """Bild med en mörk rektangel på samma plats som annoteringen.

    Bakgrunden är vit som i röntgenbilderna, så en roterad bilds nya yta
    smälter in i stället för att synas som en svart ram (TASK-105).
    """
    frame = np.full((HEIGHT, WIDTH, 3), 255, np.uint8)
    frame[3:15, 2:12] = 0
    return frame


def _annotations() -> list[dict]:
    return [{"class_name": "kniv", "bbox": list(BBOX)}]


def _content_box(frame: np.ndarray) -> tuple[int, int, int, int]:
    """Den mörka rektangelns omslutande ruta som (x, y, w, h)."""
    ys, xs = np.nonzero(frame[:, :, 0] < 255)
    return xs.min(), ys.min(), xs.max() - xs.min() + 1, ys.max() - ys.min() + 1


def _service(tmp_path) -> DatasetService:
    return DatasetService(tmp_path / "datasets")


def _sample(fill: int = 100) -> AnnotatedImage:
    frame = np.full((HEIGHT, WIDTH, 3), fill, np.uint8)
    return AnnotatedImage(frame, _annotations())


def test_rotation_keeps_the_annotation_on_the_object():
    """Rutan följer med bilden, så objektet ligger kvar i annoteringen."""
    rotated, annotations = rotate(_frame(), _annotations(), 90)

    assert rotated.shape[:2] == (WIDTH, HEIGHT)
    x, y, w, h = annotations[0]["bbox"]
    content = _content_box(rotated)
    assert abs(content[0] - x) <= 1 and abs(content[1] - y) <= 1
    assert abs(content[2] - w) <= 1 and abs(content[3] - h) <= 1


def test_rotation_widens_the_image_instead_of_cropping_it():
    """Hela den roterade bilden får plats, så inget objekt klipps bort."""
    rotated, annotations = rotate(_frame(), _annotations(), 45)

    assert rotated.shape[0] > HEIGHT and rotated.shape[1] > WIDTH
    x, y, w, h = annotations[0]["bbox"]
    assert 0 <= x and 0 <= y and x + w <= rotated.shape[1] and y + h <= rotated.shape[0]


def test_rotation_fills_the_new_area_with_the_white_background():
    """Den nya ytan matchar bildernas vita bakgrund i stället för att bli svart (TASK-105)."""
    rotated, _moved = rotate(_frame(), _annotations(), 45)

    assert rotated[0, 0].tolist() == [255, 255, 255]
    assert rotated[-1, -1].tolist() == [255, 255, 255]


def test_rotation_of_the_whole_image_fills_the_new_frame():
    """Bildens egen ruta blir den nya ramen, utan att hamna utanför den."""
    annotations = [{"class_name": "kniv", "bbox": [0, 0, WIDTH, HEIGHT]}]

    rotated, moved = rotate(_frame(), annotations, 30)

    x, y, w, h = moved[0]["bbox"]
    assert (x, y) == (0, 0)
    assert w == pytest.approx(rotated.shape[1], abs=1)
    assert h == pytest.approx(rotated.shape[0], abs=1)


def test_flip_horizontal_mirrors_the_annotation():
    flipped, annotations = flip(_frame(), _annotations(), True)

    assert annotations[0]["bbox"] == [WIDTH - (BBOX[0] + BBOX[2]), BBOX[1], BBOX[2], BBOX[3]]
    assert _content_box(flipped) == tuple(annotations[0]["bbox"])


def test_flip_vertical_mirrors_the_annotation():
    flipped, annotations = flip(_frame(), _annotations(), False)

    assert annotations[0]["bbox"] == [BBOX[0], HEIGHT - (BBOX[1] + BBOX[3]), BBOX[2], BBOX[3]]
    assert _content_box(flipped) == tuple(annotations[0]["bbox"])


def test_scale_resizes_the_image_and_the_annotation():
    scaled, annotations = scale(_frame(), _annotations(), 2.0)

    assert scaled.shape[:2] == (2 * HEIGHT, 2 * WIDTH)
    assert annotations[0]["bbox"] == [4, 6, 20, 24]


def test_scale_down_keeps_the_annotation_inside_the_image():
    scaled, annotations = scale(_frame(), _annotations(), 0.5)

    assert scaled.shape[:2] == (HEIGHT // 2, WIDTH // 2)
    x, y, w, h = annotations[0]["bbox"]
    assert x + w <= scaled.shape[1] and y + h <= scaled.shape[0]


def test_color_variation_changes_the_pixels_but_not_the_annotations():
    adjusted, annotations = adjust_color(_frame(), _annotations(), 1.0, -40)

    assert annotations[0]["bbox"] == BBOX
    # pixeln utanför rektangeln är vit och mörknar av variationen
    assert adjusted[30, 40, 0] < _frame()[30, 40, 0]


def test_plan_gives_one_type_per_image_in_per_type_mode():
    """En bild per variationstyp: en typ i taget, cykliskt över de valda (TASK-106)."""
    settings = VariationSettings(
        count=5,
        mode=MODE_PER_TYPE,
        rotation=True,
        rotation_degrees=30,
        flip_horizontal=True,
        scale=True,
        scale_percent=50,
    )

    plan = variation_plan(settings, random.Random(1))

    assert len(plan) == 5
    assert [len(variations) for variations in plan] == [1] * 5
    assert [variations[0]["type"] for variations in plan] == [
        "rotation",
        "flip",
        "scale",
        "rotation",
        "flip",
    ]


def test_plan_gives_every_type_in_each_image_in_all_mode():
    settings = VariationSettings(
        count=2,
        mode=MODE_ALL,
        rotation=True,
        rotation_degrees=30,
        flip_vertical=True,
        scale=True,
        scale_percent=50,
        color=True,
        color_percent=20,
    )

    plan = variation_plan(settings, random.Random(1))

    assert len(plan) == 2
    for variations in plan:
        assert [variation["type"] for variation in variations] == [
            "rotation",
            "flip",
            "scale",
            "color",
        ]
    assert all(abs(variations[0]["angle"]) <= 30 for variations in plan)
    assert all(variations[1]["axis"] == "vertical" for variations in plan)
    assert all(0.5 <= variations[2]["factor"] <= 1.5 for variations in plan)
    assert all(0.8 <= variations[3]["contrast"] <= 1.2 for variations in plan)


def test_plan_picks_a_random_subset_in_random_mode():
    """Slumpvisa kombinationer väljer bara bland de aktiverade typerna (TASK-106)."""
    settings = VariationSettings(
        count=20,
        mode=MODE_RANDOM,
        rotation=True,
        rotation_degrees=30,
        flip_horizontal=True,
        scale=True,
        scale_percent=50,
    )

    plan = variation_plan(settings, random.Random(4))

    assert len(plan) == 20
    assert all(variations for variations in plan), "en bild blev utan variation"
    kinds = {variation["type"] for variations in plan for variation in variations}
    assert kinds <= {"rotation", "flip", "scale"}
    assert {len(variations) for variations in plan} != {1}, "alla bilder blev lika"


def test_plan_is_empty_without_an_active_type():
    assert variation_plan(VariationSettings(count=5), random.Random(1)) == []


def test_plan_is_empty_without_a_count():
    assert variation_plan(VariationSettings(rotation=True), random.Random(1)) == []


def test_variation_plan_is_reproducible_with_a_seed():
    settings = VariationSettings(
        count=3, mode=MODE_RANDOM, rotation=True, rotation_degrees=360
    )

    first = variation_plan(settings, random.Random(7))
    second = variation_plan(settings, random.Random(7))

    assert first == second


def test_scale_is_clamped_so_the_image_never_disappears():
    settings = VariationSettings(
        count=20, mode=MODE_ALL, scale=True, scale_percent=100
    )

    plan = variation_plan(settings, random.Random(3))

    assert all(
        variation["factor"] >= 0.25
        for variations in plan
        for variation in variations
    )


def test_apply_variation_dispatches_on_the_type():
    frame, annotations = apply_variation(
        _frame(), _annotations(), {"type": "flip", "axis": "horizontal"}
    )

    assert annotations[0]["bbox"][0] == WIDTH - (BBOX[0] + BBOX[2])
    assert frame.shape[:2] == (HEIGHT, WIDTH)


def test_apply_variation_leaves_an_unknown_type_untouched():
    frame, annotations = apply_variation(_frame(), _annotations(), {"type": "okänd"})

    assert annotations[0]["bbox"] == BBOX
    assert np.array_equal(frame, _frame())


def test_apply_variations_applies_every_variation_in_order():
    """En bild kan bära flera variationer samtidigt (TASK-106)."""
    frame, annotations = apply_variations(
        _frame(),
        _annotations(),
        [
            {"type": "flip", "axis": "horizontal"},
            {"type": "scale", "factor": 2.0},
        ],
    )

    flipped_x = WIDTH - (BBOX[0] + BBOX[2])
    assert frame.shape[:2] == (2 * HEIGHT, 2 * WIDTH)
    assert annotations[0]["bbox"] == [
        2 * flipped_x,
        2 * BBOX[1],
        2 * BBOX[2],
        2 * BBOX[3],
    ]


def test_describe_names_every_variation_in_the_list():
    text = describe(
        [
            {"type": "rotation", "angle": 12.5},
            {"type": "scale", "factor": 0.75},
        ]
    )

    assert text == "rotation 12.5°, storlek 0.75×"


def test_describe_names_the_variation():
    assert describe({"type": "rotation", "angle": 12.5}) == "rotation 12.5°"
    assert describe({"type": "flip", "axis": "vertical"}) == "vänd vertikalt"
    assert describe({"type": "scale", "factor": 0.75}) == "storlek 0.75×"
    assert "kontrast" in describe({"type": "color", "contrast": 1.1, "brightness": 5})


def test_add_variations_adds_one_group_per_variation(tmp_path):
    service = _service(tmp_path)
    service.add_samples([_sample(60), _sample(120)], captured="2026-11-01T09:00:00")

    added = service.add_variations(
        VariationSettings(count=2, rotation=True, rotation_degrees=30), seed=1
    )

    assert added == 2
    images = service.load_dataset()["images"]
    assert len(images) == 6
    groups = {image["group"] for image in images if image.get("synthetic")}
    assert len(groups) == 2
    assert all(image.get("synthetic") for image in images[2:])


def test_add_variations_keeps_the_pair_together(tmp_path):
    """Båda bilderna i paret får samma variation, så paret hör ihop."""
    service = _service(tmp_path)
    service.add_samples([_sample(60), _sample(120)], captured="2026-11-01T09:00:00")

    service.add_variations(VariationSettings(count=1, flip_horizontal=True), seed=1)

    synthetic = [
        image for image in service.load_dataset()["images"] if image.get("synthetic")
    ]
    assert len(synthetic) == 2
    assert synthetic[0]["group"] == synthetic[1]["group"]
    assert synthetic[0]["variation"] == synthetic[1]["variation"]
    assert [image["source"] for image in synthetic] == [1, 2]
    assert synthetic[0]["captured"] == "2026-11-01T09:00:00"


def test_add_variations_only_varies_the_originals(tmp_path):
    """En ny utökning varierar originalen, inte de tidigare variationerna."""
    service = _service(tmp_path)
    service.add_samples([_sample(60), _sample(120)])
    settings = VariationSettings(count=1, rotation=True, rotation_degrees=20)

    service.add_variations(settings, seed=1)
    service.add_variations(settings, seed=1)

    images = service.load_dataset()["images"]
    assert len(images) == 6
    sources = {image["source"] for image in images if image.get("synthetic")}
    assert sources == {1, 2}


def test_add_variations_without_settings_changes_nothing(tmp_path):
    service = _service(tmp_path)
    service.add_samples([_sample()])

    assert service.add_variations(VariationSettings()) == 0
    assert len(service.load_dataset()["images"]) == 1


def test_add_variations_without_images_changes_nothing(tmp_path):
    service = _service(tmp_path)

    assert service.add_variations(VariationSettings(count=1, rotation=True)) == 0
    assert service.load_dataset()["images"] == []


def test_add_variations_writes_labels_for_the_varied_annotations(tmp_path):
    service = _service(tmp_path)
    service.add_samples([_sample()])

    service.add_variations(VariationSettings(count=1, scale=True, scale_percent=50), seed=2)

    images = service.load_dataset()["images"]
    synthetic = images[1]
    assert synthetic["annotations"]
    label = service.store.labels_dir / "img_000002.txt"
    assert label.exists()
    assert label.read_text(encoding="utf-8").startswith("0 ")
    assert service.metadata()["num_objects"] == 2


def test_delete_synthetic_removes_only_the_synthetic_images(tmp_path):
    service = _service(tmp_path)
    service.add_samples([_sample(60), _sample(120)])
    service.add_variations(VariationSettings(count=1, flip_horizontal=True), seed=1)

    removed = service.delete_synthetic()

    assert removed == 2
    images = service.load_dataset()["images"]
    assert [image["id"] for image in images] == [1, 2]
    assert not any(image.get("synthetic") for image in images)
    assert sorted(path.name for path in service.images_dir.iterdir()) == [
        "img_000001.png",
        "img_000002.png",
    ]
    assert sorted(path.name for path in service.store.labels_dir.iterdir()) == [
        "img_000001.txt",
        "img_000002.txt",
    ]
    assert service.metadata()["num_objects"] == 2


def test_delete_synthetic_without_synthetic_images_returns_zero(tmp_path):
    service = _service(tmp_path)
    service.add_samples([_sample()])

    assert service.delete_synthetic() == 0
    assert len(service.load_dataset()["images"]) == 1
