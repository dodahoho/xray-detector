from __future__ import annotations

from xray_detector.config import PROJECT_ROOT, AppConfig


def test_default_config_loads():
    config = AppConfig.load(PROJECT_ROOT / "nonexistent-config.yaml")
    assert config.app.dataset == "default"
    assert config.video.cam0.width == 1920
    assert config.video.cam1.index == 1
    assert config.detection.device == "cuda:0"
    assert config.data_root == PROJECT_ROOT / "data"


def test_user_config_overrides_defaults(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(
        "app:\n  dataset: custom\nvideo:\n  cam0:\n    type: test_pattern\n"
        "detection:\n  conf: 0.5\n",
        encoding="utf-8",
    )
    config = AppConfig.load(path)
    assert config.app.dataset == "custom"
    assert config.video.cam0.type == "test_pattern"
    assert config.video.cam0.width == 1920
    assert config.detection.conf == 0.5


def test_config_roundtrip(tmp_path):
    path = tmp_path / "config.yaml"
    config = AppConfig.load(path)
    config.app.dataset = "roundtrip"
    config.app.data_root = str(tmp_path / "data")
    config.dataset.jpeg_quality = 80
    config.video.cam1.type = "file"
    config.video.cam1.file = "clip.mp4"
    saved = config.save(path)

    loaded = AppConfig.load(saved)
    assert loaded.app.dataset == "roundtrip"
    assert loaded.dataset.jpeg_quality == 80
    assert loaded.video.cam1.type == "file"
    assert loaded.video.cam1.file == "clip.mp4"
    assert loaded.data_root == tmp_path / "data"
