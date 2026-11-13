"""Träningens bildstorlek följer datasetets upplösning (TASK-80)."""

import json

import numpy as np
import pytest
from PySide6.QtCore import QSettings

from xray_detector.application.dataset_service import DatasetService
from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.domain.model_input import DEFAULT_SIZE, MAX_SIZE, MIN_SIZE
from xray_detector.domain.training import imgsz_for
from xray_detector.ui.training_view import TrainingView


def _sample(width: int, height: int, fill: int = 100) -> AnnotatedImage:
    frame = np.full((height, width, 3), fill, dtype=np.uint8)
    return AnnotatedImage(frame, [{"class_name": "kniv", "bbox": [2, 2, 8, 8]}])


@pytest.fixture
def settings(tmp_path) -> QSettings:
    return QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)


def _view(config, settings) -> TrainingView:
    return TrainingView(config, DatasetService(config.dataset_dir), settings)


def test_imgsz_keeps_the_longest_side_of_the_resolution():
    assert imgsz_for(1920, 1080) == 1920
    assert imgsz_for(1280, 720) == 1280
    assert imgsz_for(640, 480) == 640


def test_imgsz_rounds_up_to_the_stride_and_stays_within_the_limits():
    assert imgsz_for(1000, 700) == 1024
    assert imgsz_for(100, 80) == MIN_SIZE
    assert imgsz_for(4000, 3000) == MAX_SIZE


def test_image_sizes_are_counted_most_common_first(tmp_path):
    service = DatasetService(tmp_path / "datasets")
    service.add_samples([_sample(640, 480), _sample(640, 480)])
    service.add_samples([_sample(1920, 1080)])

    assert service.image_sizes() == [(640, 480, 2), (1920, 1080, 1)]


def test_image_sizes_prefer_the_larger_image_on_a_tie(tmp_path):
    service = DatasetService(tmp_path / "datasets")
    service.add_samples([_sample(640, 480)])
    service.add_samples([_sample(1920, 1080)])

    assert service.image_sizes() == [(1920, 1080, 1), (640, 480, 1)]


def test_image_sizes_ignore_images_without_dimensions(tmp_path):
    """Ett äldre dataset.json kan sakna width/height och får inte krascha vyn."""
    service = DatasetService(tmp_path / "datasets")
    service.add_samples([_sample(640, 480)])
    dataset = service.load_dataset()
    dataset["images"].append({"id": 99, "file_name": "gammal.png"})
    (service.store.root / "dataset.json").write_text(json.dumps(dataset), encoding="utf-8")

    assert service.image_sizes() == [(640, 480, 1)]


def test_training_view_defaults_to_the_most_common_resolution(qapp, config, settings):
    service = DatasetService(config.dataset_dir)
    service.add_samples([_sample(1920, 1080), _sample(1920, 1080)])
    service.add_samples([_sample(640, 480)])

    view = _view(config, settings)

    assert view.imgsz_spin.value() == 1920
    assert "1920x1080 (2)" in view.imgsz_info.text()
    assert "640x480 (1)" in view.imgsz_info.text()


def test_training_view_without_dataset_keeps_the_default(qapp, config, settings):
    view = _view(config, settings)

    assert view.imgsz_spin.value() == DEFAULT_SIZE
    assert view.imgsz_info.text() == "Datasetets upplösningar: -"


def test_user_choice_survives_a_new_dataset_resolution(qapp, config, settings):
    service = DatasetService(config.dataset_dir)
    service.add_samples([_sample(1920, 1080)])
    view = _view(config, settings)

    view.imgsz_spin.setValue(640)
    service.add_samples([_sample(640, 480), _sample(640, 480)])
    view.refresh_dataset_info()

    assert view.imgsz_spin.value() == 640
    assert "640x480 (2)" in view.imgsz_info.text()


def test_saved_choice_is_restored_and_kept(qapp, config, settings):
    service = DatasetService(config.dataset_dir)
    service.add_samples([_sample(1920, 1080)])
    settings.setValue("training/imgsz", 512)

    view = _view(config, settings)
    view.restore_settings()
    view.refresh_dataset_info()

    assert view.imgsz_spin.value() == 512


def test_default_is_not_saved_so_it_keeps_following_the_dataset(qapp, config, settings):
    service = DatasetService(config.dataset_dir)
    service.add_samples([_sample(1920, 1080)])
    view = _view(config, settings)

    view.save_settings()

    assert not settings.contains("training/imgsz")
