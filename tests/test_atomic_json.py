"""Test för atomisk JSON-skrivning (TASK-3)."""

import json

import pytest

from xray_detector.infrastructure.dataset_store.json_io import atomic_write_json


def test_atomic_write_creates_and_replaces(tmp_path):
    target = tmp_path / "dataset.json"
    atomic_write_json(target, {"num": 1})
    assert json.loads(target.read_text(encoding="utf-8")) == {"num": 1}
    atomic_write_json(target, {"num": 2})
    assert json.loads(target.read_text(encoding="utf-8")) == {"num": 2}
    # ingen tempfil latar sig
    assert list(tmp_path.iterdir()) == [target]


def test_atomic_write_keeps_old_file_on_crash(tmp_path, monkeypatch):
    target = tmp_path / "dataset.json"
    atomic_write_json(target, {"num": 1})

    def broken_dump(payload, file, **kwargs):
        raise RuntimeError("strömavbrott mitt i skrivningen")

    monkeypatch.setattr("xray_detector.infrastructure.dataset_store.json_io.json.dump", broken_dump)
    with pytest.raises(RuntimeError):
        atomic_write_json(target, {"num": 2})

    # gamla intakta filen finns kvar, och inga tempfiler städjer sig inte
    assert json.loads(target.read_text(encoding="utf-8")) == {"num": 1}
    assert list(tmp_path.iterdir()) == [target]


def test_store_and_export_still_work(tmp_path):
    import numpy as np

    from xray_detector.application.dataset_service import DatasetService
    from xray_detector.domain.dataset import AnnotatedImage

    service = DatasetService(tmp_path / "datasets")
    service.add_samples([AnnotatedImage(np.zeros((20, 30, 3), np.uint8),
                                        [{"class_name": "kniv", "bbox": [1, 2, 3, 4]}])])
    assert json.loads((service.store.root / "dataset.json").read_text(encoding="utf-8"))["images"]
    service.export_yolo(tmp_path / "exports")
    manifest = json.loads((tmp_path / "exports" / "yolo" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["num_images"] == 1
