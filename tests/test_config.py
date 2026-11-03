from __future__ import annotations

from xray_detector.config import default_config, load_config, save_config


def test_save_and_load_config(tmp_path) -> None:
    config = default_config()
    config.video.camera_left = 3
    config.video.camera_right = 5
    config.detection.confidence = 0.75
    config.detection.class_filter = [1, 2]
    config.app.active_dataset = "linje-a"
    path = tmp_path / "config.toml"
    save_config(config, path)
    loaded = load_config(path)
    assert loaded.video.camera_left == 3
    assert loaded.video.camera_right == 5
    assert loaded.detection.confidence == 0.75
    assert loaded.detection.class_filter == [1, 2]
    assert loaded.app.active_dataset == "linje-a"


def test_missing_config_returns_defaults(tmp_path) -> None:
    loaded = load_config(tmp_path / "missing.toml")
    assert loaded.video.camera_left == 0
    assert loaded.detection.model == "yolo11n.pt"
