"""Konfigfil och loggning (TASK-15)."""

import logging
from pathlib import Path

import pytest

from xray_detector.application.app_config import (
    apply_yaml_overrides,
    load_config_with_yaml,
    setup_logging,
)
from xray_detector.domain.config import AppConfig


def test_yaml_overrides_classes_model_and_threshold(tmp_path):
    config = AppConfig()
    yaml = tmp_path / "config.yaml"
    yaml.write_text(
        "# kommentar\n"
        "classes: ['cigaretter', 'kniv', 'vattenpistol']\n"
        "default_model: yolo26s\n"
        "confidence_threshold: 0.55\n",
        encoding="utf-8",
    )
    assert apply_yaml_overrides(config, yaml)
    assert config.classes == ["cigaretter", "kniv", "vattenpistol"]
    assert config.default_model == "yolo26s"
    assert config.confidence_threshold == 0.55


def test_missing_yaml_is_noop(tmp_path):
    config = AppConfig()
    baseline = list(config.classes)
    assert not apply_yaml_overrides(config, tmp_path / "saknas.yaml")
    assert config.classes == baseline


def test_load_config_prefers_data_dir_file(tmp_path):
    workdir = tmp_path / "work"
    workdir.mkdir()
    (workdir / "config.yaml").write_text("default_model: yolo26m\n", encoding="utf-8")
    datadir = tmp_path / "data"
    datadir.mkdir()
    (datadir / "config.yaml").write_text("default_model: yolo26n\n", encoding="utf-8")

    config, used = load_config_with_yaml(config_dir=datadir, workdir=workdir)
    assert used == datadir / "config.yaml"
    assert config.default_model == "yolo26n"


def test_load_config_falls_back_to_workdir(tmp_path):
    workdir = tmp_path / "work"
    workdir.mkdir()
    (workdir / "config.yaml").write_text("default_model: yolo26s\n", encoding="utf-8")
    config, used = load_config_with_yaml(config_dir=tmp_path / "saknas", workdir=workdir)
    assert used == workdir / "config.yaml"
    assert config.default_model == "yolo26s"


def test_setup_logging_rotates_to_file(tmp_path):
    log = setup_logging(tmp_path / "logs")
    log.warning("test-varning 123")
    for handler in logging.getLogger().handlers[:]:
        handler.flush()
    content = (tmp_path / "logs" / "app.log").read_text(encoding="utf-8")
    assert "test-varning 123" in content
    assert "WARNING" in content
    # idempotent: ingen dubbel handler
    setup_logging(tmp_path / "logs")
    rotating = [h for h in logging.getLogger().handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
    assert len(rotating) == 1
