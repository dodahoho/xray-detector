"""Schemalagd träning (TASK-7): nattfönster, inaktivitet, kö och avbokning."""

from datetime import datetime, time

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QMessageBox

from xray_detector.application.training_service import TrainingScheduler, TrainingService
from xray_detector.domain.training import TrainConfig


def make_scheduler(qapp):
    service = TrainingService()
    workers = []
    service.worker_created.connect(workers.append)
    return service.scheduler(), service, workers


def make_config(tmp_path):
    return TrainConfig(
        dataset_yaml=tmp_path / "d.yaml",
        weights="yolo26n.pt",
        output_dir=tmp_path / "o",
        epochs=1,
    )


def test_night_window_wrap(qapp):
    scheduler, _, _ = make_scheduler(qapp)
    scheduler.night_start = time(23, 0)
    scheduler.night_end = time(5, 0)
    assert scheduler.night_window_active(datetime(2026, 1, 1, 23, 30))
    assert scheduler.night_window_active(datetime(2026, 1, 1, 3, 0))
    assert not scheduler.night_window_active(datetime(2026, 1, 1, 12, 0))


def test_night_window_same_day(qapp):
    scheduler, _, _ = make_scheduler(qapp)
    scheduler.night_start = time(1, 0)
    scheduler.night_end = time(4, 0)
    assert scheduler.night_window_active(datetime(2026, 1, 1, 2, 0))
    assert not scheduler.night_window_active(datetime(2026, 1, 1, 5, 0))


def test_queued_night_job_waits_for_window(qapp, tmp_path):
    scheduler, service, workers = make_scheduler(qapp)
    # övertydligt omöjligt fönster: 1 minut fran nu+i1 timme
    now = datetime.now()
    far_away = f"{(now.hour + 1) % 24:02d}:59"
    scheduler.queue_job(make_config(tmp_path), "night", night_start=far_away, night_end=far_away)
    assert scheduler.has_queued()
    scheduler._check()
    assert workers == [], "jobbet far inte starta utanfor fönstret"
    # avboka
    scheduler.cancel()
    assert not scheduler.has_queued()


def test_queued_night_job_starts_inside_window(qapp, tmp_path):
    scheduler, service, workers = make_scheduler(qapp)
    service.create_worker = lambda config: workers.append(config)  # undvik riktig process
    now_hour = f"{datetime.now().hour:02d}"
    scheduler.queue_job(make_config(tmp_path), "night",
                        night_start=f"{now_hour}:00", night_end="23:59")
    scheduler._check()
    assert len(workers) == 1, "jobbet skulle starta inne i fönstret"


def test_inactivity_job_waits_and_starts(qapp, tmp_path):
    scheduler, service, workers = make_scheduler(qapp)
    service.create_worker = lambda config: workers.append(config)
    scheduler.queue_job(make_config(tmp_path), "inactivity", inactivity_minutes=30)
    scheduler.record_activity()
    scheduler._check()
    assert workers == [], "far inte starta direkt efter aktivitet"
    # simulera 31 minuters inaktivitet
    scheduler._last_activity -= 31 * 60
    assert scheduler.condition_met()
    scheduler._check()
    assert len(workers) == 1


def test_queued_status_messages(qapp, tmp_path):
    scheduler, _, _ = make_scheduler(qapp)
    messages = []
    scheduler.status_changed.connect(messages.append)
    scheduler.queue_job(make_config(tmp_path), "night", night_start="23:00", night_end="05:00")
    assert any("23:00" in message and "05:00" in message for message in messages)
    scheduler.cancel()
    assert any("avbokat" in message for message in messages)


def test_training_view_queue_flow(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No))
    from xray_detector.domain.config import AppConfig
    from xray_detector.ui.main_window import MainWindow
    from xray_detector.ui.training_view import TrainingView
    from xray_detector.domain.dataset import AnnotatedImage
    import numpy as np

    from xray_detector.application.dataset_service import DatasetService

    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    window = MainWindow(config)
    view = window.training_view
    view.dataset_service.add_samples([AnnotatedImage(np.zeros((20, 30, 3), np.uint8),
                                                        [{"class_name": "kniv", "bbox": [1, 1, 4, 4]}])])
    view.refresh_dataset_info()
    assert view.run_combo.count() == 3
    index = view.run_combo.findData("night")
    view.run_combo.setCurrentIndex(index)
    started = []
    view.training_service.create_worker = lambda cfg: started.append(cfg)
    view._on_start()
    assert started == [], "natt-kat jobb startar inga workers direkt"
    assert view.training_service.scheduler().has_queued()
    # Avbryt avbokar det koade jobbet
    view._on_abort()
    assert not view.training_service.scheduler().has_queued()
