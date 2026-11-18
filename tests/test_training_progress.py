"""Förlopp inom pågående epok (TASK-96): eventraden, throttlingen och
inaktuella heartbeats."""

import sys
import time
from types import SimpleNamespace

from xray_detector.domain.training import (
    PROGRESS_STALE_AFTER_S,
    ProgressEvent,
    TrainConfig,
)
from xray_detector.infrastructure.training.progress import (
    PROGRESS_MARKER,
    ProgressReporter,
    parse_progress_line,
    progress_line,
)

# --- Eventraden över processgränsen ---


def test_progress_line_round_trips():
    event = ProgressEvent(epoch=3, step=45, total_steps=120, updated=1000.0)

    parsed = parse_progress_line(progress_line(event))

    assert parsed == event
    assert parsed.fraction == 45 / 120


def test_progress_line_ignores_other_output():
    assert parse_progress_line("vanlig rad") is None
    assert parse_progress_line(f"{PROGRESS_MARKER}inte json") is None
    assert parse_progress_line(f"{PROGRESS_MARKER}{{\"epoch\": 1}}") is None


def test_summary_is_readable():
    event = ProgressEvent(epoch=3, step=45, total_steps=120, updated=0.0)

    assert event.summary() == "Epok 3 · steg 45/120 (38 %)"


def test_a_zero_step_epoch_does_not_divide_by_zero():
    assert ProgressEvent(epoch=1, step=0, total_steps=0, updated=0.0).fraction == 0.0


# --- Throttlingen ---


def test_reporter_throttles_the_writes():
    now = [100.0]
    lines: list[str] = []
    reporter = ProgressReporter(interval=2.0, clock=lambda: now[0], emit=lines.append)

    reporter.update(1, 1, 100)
    now[0] += 0.5
    reporter.update(1, 2, 100)
    now[0] += 0.5
    reporter.update(1, 3, 100)
    now[0] += 2.0
    reporter.update(1, 4, 100)

    assert len(lines) == 2
    assert parse_progress_line(lines[-1]).step == 4


def test_reporter_reports_a_new_epoch_immediately():
    now = [100.0]
    lines: list[str] = []
    reporter = ProgressReporter(interval=2.0, clock=lambda: now[0], emit=lines.append)

    reporter.update(1, 100, 100)
    now[0] += 0.1
    reporter.update(2, 1, 100)

    assert [parse_progress_line(line).epoch for line in lines] == [1, 2]


def test_reporter_always_reports_the_last_step_of_an_epoch():
    now = [100.0]
    lines: list[str] = []
    reporter = ProgressReporter(interval=2.0, clock=lambda: now[0], emit=lines.append)

    reporter.update(1, 99, 100)
    now[0] += 0.1
    reporter.update(1, 100, 100, force=True)

    assert parse_progress_line(lines[-1]).step == 100


# --- Inaktuell heartbeat ---


def test_a_fresh_heartbeat_is_current():
    event = ProgressEvent(epoch=1, step=10, total_steps=100, updated=1000.0)

    assert not event.is_stale(1000.0 + PROGRESS_STALE_AFTER_S / 2)


def test_an_old_heartbeat_is_recognised_as_stale():
    event = ProgressEvent(epoch=1, step=10, total_steps=100, updated=1000.0)

    assert event.is_stale(1000.0 + PROGRESS_STALE_AFTER_S + 1)
    assert event.age(1000.0 + PROGRESS_STALE_AFTER_S + 1) > PROGRESS_STALE_AFTER_S


def test_a_heartbeat_from_the_future_is_not_stale():
    """Klockan i träningsprocessen och vyn kan gå isär något."""
    event = ProgressEvent(epoch=1, step=10, total_steps=100, updated=1005.0)

    assert event.age(1000.0) == 0.0
    assert not event.is_stale(1000.0)


# --- Träningsprocessen ---


def test_yolo_batch_callback_reports_the_step():
    from xray_detector.infrastructure.training.train_task import _batch_callback

    lines: list[str] = []
    callback = _batch_callback(ProgressReporter(interval=0, emit=lines.append))
    trainer = SimpleNamespace(epoch=0, train_loader=[0] * 4)

    for _ in range(4):
        callback(trainer)

    event = parse_progress_line(lines[-1])
    assert (event.epoch, event.step, event.total_steps) == (1, 4, 4)


def test_yolo_batch_callback_counts_the_steps_per_epoch():
    from xray_detector.infrastructure.training.train_task import _batch_callback

    lines: list[str] = []
    callback = _batch_callback(ProgressReporter(interval=0, emit=lines.append))
    trainer = SimpleNamespace(epoch=0, train_loader=[0] * 2)

    callback(trainer)
    callback(trainer)
    trainer.epoch = 1
    callback(trainer)

    events = [parse_progress_line(line) for line in lines]
    assert [(event.epoch, event.step) for event in events] == [(1, 1), (1, 2), (2, 1)]


def test_yolo_batch_callback_without_a_loader_stays_quiet():
    from xray_detector.infrastructure.training.train_task import _batch_callback

    lines: list[str] = []
    callback = _batch_callback(ProgressReporter(interval=0, emit=lines.append))

    callback(SimpleNamespace(epoch=0, train_loader=None))

    assert lines == []


# --- TrainingWorker ---


def _worker(qapp, tmp_path, script):
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


def _wait_for_qt(qapp, predicate, timeout_ms=8000, step_ms=20):
    elapsed = 0
    while elapsed < timeout_ms:
        qapp.processEvents()
        if predicate():
            return True
        time.sleep(step_ms / 1000)
        elapsed += step_ms
    return False


def test_worker_emits_the_progress_event(qapp, tmp_path):
    event = ProgressEvent(epoch=2, step=30, total_steps=60, updated=1000.0)
    script = (
        "import sys\n"
        f"sys.stdout.write({progress_line(event)!r} + '\\n')\n"
        "sys.stdout.flush()\n"
    )
    worker = _worker(qapp, tmp_path, script)
    events = []
    results = []
    worker.progress_event.connect(events.append)
    worker.finished_training.connect(lambda ok, msg: results.append(ok))
    worker.start()

    assert _wait_for_qt(qapp, lambda: bool(results))

    assert events == [event]


def test_worker_finds_the_progress_event_after_a_progress_bar(qapp, tmp_path):
    """tqdm skriver utan radbrytning, så eventet kan hamna mitt i en rad."""
    event = ProgressEvent(epoch=1, step=5, total_steps=10, updated=1000.0)
    script = (
        "import sys\n"
        f"sys.stdout.write('Epok 1: 50%|' + {progress_line(event)!r} + '\\n')\n"
        "sys.stdout.flush()\n"
    )
    worker = _worker(qapp, tmp_path, script)
    events = []
    lines = []
    results = []
    worker.progress_event.connect(events.append)
    worker.progress.connect(lines.append)
    worker.finished_training.connect(lambda ok, msg: results.append(ok))
    worker.start()

    assert _wait_for_qt(qapp, lambda: bool(results))

    assert events == [event]
    assert any("Epok 1: 50%" in line for line in lines)


# --- Träningsvyn ---


def _view(qapp, tmp_path):
    from PySide6.QtCore import QSettings

    from xray_detector.domain.config import AppConfig
    from xray_detector.infrastructure.dataset_store.store import DatasetStore
    from xray_detector.ui.training_view import TrainingView

    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    return TrainingView(config, DatasetStore(config.dataset_dir), settings)


def test_training_view_shows_the_epoch_progress(qapp, tmp_path):
    view = _view(qapp, tmp_path)

    view._on_progress_event(
        ProgressEvent(epoch=3, step=45, total_steps=120, updated=time.time())
    )

    assert view.epoch_progress_label.text() == "Epok 3 · steg 45/120 (38 %)"


def test_training_view_marks_an_old_heartbeat_as_stale(qapp, tmp_path):
    view = _view(qapp, tmp_path)

    view._on_progress_event(
        ProgressEvent(
            epoch=3,
            step=45,
            total_steps=120,
            updated=time.time() - PROGRESS_STALE_AFTER_S - 5,
        )
    )

    assert "ingen rapport" in view.epoch_progress_label.text()


def test_finishing_the_training_clears_the_epoch_progress(qapp, tmp_path):
    """Ett avbrott får inte lämna kvar ett förlopp som ser pågående ut."""
    view = _view(qapp, tmp_path)
    view._on_progress_event(
        ProgressEvent(epoch=3, step=45, total_steps=120, updated=time.time())
    )

    view._on_finished(False, "Träning avslutad (kod 1)")

    assert view.epoch_progress_label.text() == ""
    assert view._progress_event is None


def test_an_abort_clears_the_epoch_progress(qapp, tmp_path):
    view = _view(qapp, tmp_path)
    view._on_progress_event(
        ProgressEvent(epoch=3, step=45, total_steps=120, updated=time.time())
    )

    view._on_abort_reason("Överträning")

    assert view.epoch_progress_label.text() == ""
