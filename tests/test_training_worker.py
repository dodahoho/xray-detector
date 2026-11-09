"""QProcess-baserad träningsprocess (TASK-6): streaming, avbrott, VRAM, stängning."""

import sys
import time
from types import SimpleNamespace

from PySide6.QtCore import QSettings
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMessageBox

from xray_detector.domain.training import TrainConfig


def wait_for(qapp, predicate, timeout_ms=8000, step_ms=20):
    elapsed = 0
    while elapsed < timeout_ms:
        qapp.processEvents()
        if predicate():
            return True
        time.sleep(step_ms / 1000)
        elapsed += step_ms
    return False


def make_worker(qapp, tmp_path, script):
    from xray_detector.infrastructure.training.trainer import TrainingWorker

    config = TrainConfig(
        dataset_yaml=tmp_path / "d.yaml",
        weights="yolo26n.pt",
        output_dir=tmp_path / "o",
        epochs=1,
    )
    worker = TrainingWorker(config)
    worker.command = lambda: [sys.executable, "-c", script]
    return worker


def test_qprocess_streams_progress_and_finish(qapp, tmp_path):
    worker = make_worker(qapp, tmp_path, "print('rad ett'); print('TRAINING_DONE'); print('rad tre')")
    lines = []
    results = []
    worker.progress.connect(lines.append)
    worker.finished_training.connect(lambda ok, msg: results.append((ok, msg)))
    worker.start()
    assert wait_for(qapp, lambda: bool(results)), "finished_training kom aldrig"
    assert results[0][0] is True, results
    assert "rad ett" in lines and "TRAINING_DONE" in lines and "rad tre" in lines
    assert not worker.is_running()


def test_cancel_terminates_long_running_process(qapp, tmp_path):
    worker = make_worker(qapp, tmp_path, "import time; time.sleep(30); print('klar')")
    results = []
    worker.finished_training.connect(lambda ok, msg: results.append((ok, msg)))
    worker.start()
    assert wait_for(qapp, worker.is_running), "processen startade inte"
    worker.cancel()
    assert wait_for(qapp, lambda: len(results) == 1), "processen avbröts inte"
    assert results[0][0] is False
    assert not worker.is_running()


def test_pause_detection_releases_vram(qapp, tmp_path, monkeypatch):
    from xray_detector.domain.config import AppConfig
    from xray_detector.ui.detection_view import DetectionView

    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    view = DetectionView(config, QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))

    calls = {"empty_cache": 0}
    fake_torch = SimpleNamespace(
        cuda=SimpleNamespace(
            is_available=lambda: True,
            empty_cache=lambda: calls.__setitem__("empty_cache", calls["empty_cache"] + 1),
        )
    )
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    rebuilt = []
    monkeypatch.setattr(view, "_on_model_changed", lambda: rebuilt.append(True))

    view.detector = object()
    view.pause_detection()
    assert view.detector is None
    assert calls["empty_cache"] == 1
    view.resume_detection()
    assert rebuilt, "resume ska aterbygga detektorn efter VRAM-frigoring"


def test_close_with_running_training_asks_and_cancels(qapp, tmp_path, monkeypatch):
    from xray_detector.domain.config import AppConfig
    from xray_detector.ui.main_window import MainWindow

    cancelled = []
    fake_worker = SimpleNamespace(
        is_running=lambda: True,
        cancel=lambda: cancelled.append(True),
    )
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    window = MainWindow(config)
    window.training_view.worker = fake_worker
    event = QCloseEvent()
    window.closeEvent(event)
    assert cancelled, "trainingsprocessen avbröts inte vid stängning"

    # svar nej: notable stangning
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No))
    window.training_view.worker = fake_worker
    event = QCloseEvent()
    window.closeEvent(event)
    assert not event.isAccepted(), "stängning skulle ha stoppats vid svar nej"
    assert len(cancelled) == 1
