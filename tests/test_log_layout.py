"""Loggarnas placering under logs/ (TASK-51)."""

import logging
import os
from pathlib import Path

import pytest
from PySide6.QtCore import QObject, QSettings, Signal

from xray_detector.application.app_config import (
    LOG_BACKUP_COUNT,
    LOG_MAX_BYTES,
    apply_yaml_overrides,
    file_logger,
    log_path,
    setup_logging,
)
from xray_detector.application.dataset_service import DatasetService
from xray_detector.domain.config import PROJECT_ROOT, AppConfig
from xray_detector.domain.training import TrainConfig


def _config(tmp_path: Path) -> AppConfig:
    config = AppConfig()
    config.data_dir = tmp_path / "data"
    config.logs_dir = tmp_path / "logs"
    config.ensure_dirs()
    return config


@pytest.fixture
def root_handlers():
    """Städar rot-loggerns handlare så testerna inte skriver i varandras filer."""
    root = logging.getLogger()
    before = list(root.handlers)
    yield
    for handler in list(root.handlers):
        if handler not in before:
            root.removeHandler(handler)
            handler.close()


# --- Sökvägsuppslag (AC 1, 4, 5) ---


def test_logs_dir_is_project_logs_regardless_of_workdir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = AppConfig()
    assert config.logs_dir == PROJECT_ROOT / "logs"
    assert config.logs_dir.is_absolute()


def test_ensure_dirs_creates_logs_dir(tmp_path):
    config = _config(tmp_path)
    assert config.logs_dir.is_dir()


def test_yaml_logs_dir_override(tmp_path):
    config = AppConfig()
    yaml = tmp_path / "config.yaml"

    yaml.write_text("logs_dir: logs\n", encoding="utf-8")
    assert apply_yaml_overrides(config, yaml)
    assert config.logs_dir == PROJECT_ROOT / "logs"

    absolute = tmp_path / "loggar"
    yaml.write_text(f"logs_dir: {absolute.as_posix()}\n", encoding="utf-8")
    assert apply_yaml_overrides(config, yaml)
    assert config.logs_dir == absolute


# --- Applikationsloggen (AC 1, 3) ---


def test_setup_logging_writes_app_log_under_logs_dir(tmp_path, root_handlers):
    log = setup_logging(tmp_path / "logs")
    log.warning("applikationslogg 456")
    for handler in logging.getLogger().handlers:
        handler.flush()

    content = (tmp_path / "logs" / "app.log").read_text(encoding="utf-8")
    assert "applikationslogg 456" in content
    assert not (tmp_path / "app.log").exists()


def test_setup_logging_limits_file_size(tmp_path, root_handlers):
    setup_logging(tmp_path / "logs")
    handler = next(
        h
        for h in logging.getLogger().handlers
        if isinstance(h, logging.handlers.RotatingFileHandler)
        and h.baseFilename == os.path.abspath(tmp_path / "logs" / "app.log")
    )
    assert handler.maxBytes == LOG_MAX_BYTES
    assert handler.backupCount == LOG_BACKUP_COUNT


# --- Fler loggtyper (AC 6) ---


def test_log_path_names_each_log_type(tmp_path):
    assert log_path(tmp_path, "app") == tmp_path / "app.log"
    assert log_path(tmp_path, "training") == tmp_path / "training.log"
    assert log_path(tmp_path, "export") == tmp_path / "export.log"


def test_new_log_type_needs_only_a_name(tmp_path):
    logger = file_logger("xray.test.export", log_path(tmp_path, "export"))
    logger.info("exporterade v1")
    for handler in logger.handlers:
        handler.flush()

    assert "exporterade v1" in (tmp_path / "export.log").read_text(encoding="utf-8")
    assert not (tmp_path / "app.log").exists()


def test_file_logger_rotates_when_large(tmp_path):
    logger = file_logger("xray.test.rotate", log_path(tmp_path, "rotate"))
    for _ in range(12):
        logger.info("x" * 100_000)
    for handler in logger.handlers:
        handler.flush()

    assert (tmp_path / "rotate.log.1").exists()


# --- Träningsloggen (AC 2) ---


class _FakeWorker(QObject):
    """Träningsworker utan process: signalerna räcker för loggtestet."""

    progress = Signal(str)
    finished_training = Signal(bool, str)

    def __init__(self, config: TrainConfig) -> None:
        super().__init__()
        self.config = config
        self.started = False

    def start(self) -> None:
        self.started = True

    def is_running(self) -> bool:
        return False


def _training_view(qapp, config: AppConfig):
    from xray_detector.ui.training_view import TrainingView

    dataset = DatasetService(config.dataset_dir, config.classes)
    settings = QSettings(str(config.data_dir / "s.ini"), QSettings.Format.IniFormat)
    return TrainingView(config, dataset, settings)


def _train_config(config: AppConfig, tmp_path: Path) -> TrainConfig:
    return TrainConfig(
        dataset_yaml=tmp_path / "data.yaml",
        weights=str(config.models_dir / "yolo26m.pt"),
        output_dir=config.trained_dir / "v1",
        epochs=2,
    )


def test_training_log_contains_process_output(qapp, tmp_path):
    config = _config(tmp_path)
    view = _training_view(qapp, config)
    worker = _FakeWorker(_train_config(config, tmp_path))

    view._on_worker_created(worker)
    worker.progress.emit("rad ett")
    worker.progress.emit("TRAINING_DONE")
    worker.finished_training.emit(True, "Träning avslutad (kod 0)")

    content = (config.logs_dir / "training.log").read_text(encoding="utf-8")
    assert worker.started
    assert "Startar träning" in content
    assert "rad ett" in content
    assert "TRAINING_DONE" in content
    assert "Träning avslutad (kod 0)" in content
    assert str(config.trained_dir / "v1") in content


def test_training_log_separates_runs(qapp, tmp_path):
    config = _config(tmp_path)
    view = _training_view(qapp, config)

    for run in ("v1", "v2"):
        worker = _FakeWorker(_train_config(config, tmp_path))
        worker.config.output_dir = config.trained_dir / run
        view._on_worker_created(worker)
        worker.progress.emit(f"tränade {run}")
        worker.finished_training.emit(True, "Träning avslutad (kod 0)")

    content = (config.logs_dir / "training.log").read_text(encoding="utf-8")
    assert content.count("Startar träning") == 2
    assert "tränade v1" in content and "tränade v2" in content


def test_training_log_is_not_written_to_app_log(qapp, tmp_path, root_handlers):
    config = _config(tmp_path)
    setup_logging(config.logs_dir)
    view = _training_view(qapp, config)
    worker = _FakeWorker(_train_config(config, tmp_path))

    view._on_worker_created(worker)
    worker.progress.emit("bara i träningsloggen")
    for handler in logging.getLogger().handlers:
        handler.flush()

    app_log = (config.logs_dir / "app.log").read_text(encoding="utf-8")
    assert "bara i träningsloggen" not in app_log
