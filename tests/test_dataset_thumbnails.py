"""Thumbnails med inritade detektioner i datasetvyn (TASK-64)."""

import os

import pytest

from tests.conftest import synthetic_frame
from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.infrastructure.dataset_store.store import DatasetStore
from xray_detector.ui.colors import class_color
from xray_detector.ui.dataset_view import THUMB_HEIGHT, DatasetView


def _sample(annotations: list[dict]) -> AnnotatedImage:
    return AnnotatedImage(synthetic_frame(60), annotations)


@pytest.fixture
def service(tmp_path) -> DatasetStore:
    return DatasetStore(tmp_path / "datasets")




def _built(config, service, settings) -> DatasetView:
    view = DatasetView(config, service, settings)
    view.refresh()
    view.wait_for_refresh()
    return view


def _colors(pixmap, left: int = 0, top: int = 0, right: int | None = None,
            bottom: int | None = None) -> set[str]:
    """Färgerna i ett rektangulärt område av thumbnailen."""
    image = pixmap.toImage()
    right = image.width() if right is None else right
    bottom = image.height() if bottom is None else bottom
    return {
        image.pixelColor(x, y).name()
        for x in range(left, right)
        for y in range(top, bottom)
    }


def test_thumbnail_draws_the_box_where_the_annotation_is(qapp, config, service, settings):
    """Ramen hamnar över objektet, inte i bildens motsatta hörn."""
    service.add_samples(
        [_sample([{"class_name": "pistol", "bbox": [2, 2, 8, 8]}])],
        captured="2026-11-10T09:00:00",
    )

    view = _built(config, service, settings)
    pixmap = view._thumbs[0].picture.pixmap()
    expected = class_color("pistol").name()

    assert expected in _colors(pixmap, 0, 0, pixmap.width() // 2, pixmap.height() // 2)
    assert expected not in _colors(
        pixmap, pixmap.width() // 2, pixmap.height() // 2, pixmap.width(), pixmap.height()
    )


def test_thumbnail_without_annotations_is_left_undrawn(qapp, config, service, settings):
    service.add_samples([_sample([])], captured="2026-11-10T09:00:00")

    view = _built(config, service, settings)

    expected = class_color("pistol").name()
    assert expected not in _colors(view._thumbs[0].picture.pixmap())


# --- Nedskalning och cache (TASK-149) ---


def test_thumbnails_are_scaled_down_in_the_worker(qapp, config, service, settings):
    """Bara tumnaglar ligger i minnet, inte bilderna i full upplösning."""
    service.add_samples([_sample([]), _sample([])], captured="2026-11-10T09:00:00")

    view = _built(config, service, settings)

    assert view._thumb_cache
    assert all(image.height() == THUMB_HEIGHT for image in view._thumb_cache.values())


def test_refresh_reuses_cached_thumbnails(qapp, config, service, settings):
    """En omladdning avkodar bara nya och ändrade bilder (TASK-149)."""
    service.add_samples([_sample([]), _sample([])], captured="2026-11-10T09:00:00")
    view = _built(config, service, settings)
    first = dict(view._thumb_cache)
    assert first

    view.refresh()
    view.wait_for_refresh()

    assert view._thumb_cache.keys() == first.keys()
    # samma QImage-instanser betyder att bilderna inte avkodades om
    assert all(view._thumb_cache[key] is image for key, image in first.items())


def test_a_changed_image_is_decoded_again(qapp, config, service, settings):
    service.add_samples([_sample([])], captured="2026-11-10T09:00:00")
    view = _built(config, service, settings)
    (key, first), = view._thumb_cache.items()
    path = service.images_dir / view._dataset["images"][0]["file_name"]
    os.utime(path, ns=(1, 1))

    view.refresh()
    view.wait_for_refresh()

    # ny mtime ger en ny cache-nyckel och en ny avkodning
    assert key not in view._thumb_cache
    assert len(view._thumb_cache) == 1
    assert next(iter(view._thumb_cache.values())) is not first
