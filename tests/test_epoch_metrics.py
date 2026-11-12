"""Epokvisa träningsvärden från träningsprocessen till GUI:t (TASK-44)."""

import json
import sys
import time

from xray_detector.domain.training import EpochMetrics, TrainConfig
from xray_detector.infrastructure.training.epoch_metrics import (
    EPOCH_MARKER,
    EpochAccumulator,
    EpochReporter,
    MetricsTail,
    parse_event_line,
    parse_rfdetr_row,
    parse_yolo_row,
    read_epoch_history,
)

YOLO_HEADER = (
    "epoch,time,train/box_loss,train/cls_loss,train/dfl_loss,"
    "metrics/precision(B),metrics/recall(B),metrics/mAP50(B),metrics/mAP50-95(B),"
    "val/box_loss,val/cls_loss,val/dfl_loss,lr/pg0\n"
)
YOLO_ROW = (
    "1,12.5,1.1,0.9,1.3,0.71,0.65,0.62,0.41,1.2,1.0,1.4,0.01\n"
)

RFDETR_HEADER = "epoch,step,train/loss,val/loss,val/mAP_50,val/mAP_50_95,val/precision,val/recall\n"


def _yolo_row(**overrides) -> dict:
    row = {
        "epoch": "1",
        "train/box_loss": "1.1",
        "train/cls_loss": "0.9",
        "train/dfl_loss": "1.3",
        "metrics/precision(B)": "0.71",
        "metrics/recall(B)": "0.65",
        "metrics/mAP50(B)": "0.62",
        "metrics/mAP50-95(B)": "0.41",
        "val/box_loss": "1.2",
        "val/cls_loss": "1.0",
        "val/dfl_loss": "1.4",
    }
    row.update(overrides)
    return row


# --- Parsning av respektive familjs format (AC 1, 2, 3, 8) ---


def test_yolo_row_becomes_a_complete_epoch_event():
    metrics = parse_yolo_row(_yolo_row(), total_epochs=10)

    assert metrics.epoch == 1  # results.csv är ettabaserad
    assert metrics.total_epochs == 10
    assert round(metrics.train_loss, 3) == 3.3  # summan av box/cls/dfl
    assert round(metrics.val_loss, 3) == 3.6
    assert metrics.map50 == 0.62
    assert metrics.map50_95 == 0.41
    assert metrics.precision == 0.71
    assert metrics.recall == 0.65


def test_yolo_row_without_epoch_is_ignored():
    assert parse_yolo_row({"train/box_loss": "1.0"}, total_epochs=5) is None


def test_rfdetr_row_reads_lightning_columns():
    metrics = parse_rfdetr_row(
        {
            "epoch": "2",
            "train/loss": "1.5",
            "val/loss": "1.7",
            "val/mAP_50": "0.55",
            "val/mAP_50_95": "0.33",
            "val/precision": "0.6",
            "val/recall": "0.5",
        },
        total_epochs=8,
    )

    assert metrics.epoch == 3
    assert metrics.total_epochs == 8
    assert metrics.train_loss == 1.5
    assert metrics.val_loss == 1.7
    assert metrics.map50 == 0.55
    assert metrics.map50_95 == 0.33
    assert metrics.precision == 0.6
    assert metrics.recall == 0.5


def test_rfdetr_row_without_values_leaves_them_empty():
    metrics = parse_rfdetr_row({"epoch": "0", "train/loss": "2.0"}, total_epochs=4)

    assert metrics.train_loss == 2.0
    assert metrics.val_loss is None
    assert metrics.map50_95 is None


def test_rfdetr_accumulator_merges_train_and_val_rows():
    """Lightning skriver en rad per loggning; epoken blir komplett av båda."""
    accumulator = EpochAccumulator("rfdetr", total_epochs=5)

    assert accumulator.feed({"epoch": "0", "train/loss": "2.0"}) is None
    metrics = accumulator.feed(
        {"epoch": "0", "val/loss": "2.2", "val/mAP_50_95": "0.3"}
    )

    assert metrics is not None
    assert metrics.epoch == 1
    assert metrics.train_loss == 2.0
    assert metrics.val_loss == 2.2
    assert metrics.map50_95 == 0.3


def test_rfdetr_accumulator_merges_in_the_other_order():
    accumulator = EpochAccumulator("rfdetr", total_epochs=5)

    assert accumulator.feed({"epoch": "0", "val/mAP_50_95": "0.3"}) is None
    metrics = accumulator.feed({"epoch": "0", "train/loss": "2.0"})

    assert metrics is not None
    assert metrics.train_loss == 2.0
    assert metrics.map50_95 == 0.3


def test_rfdetr_accumulator_emits_each_epoch_once():
    accumulator = EpochAccumulator("rfdetr", total_epochs=5)
    accumulator.feed({"epoch": "0", "train/loss": "2.0"})
    assert accumulator.feed({"epoch": "0", "val/mAP_50_95": "0.3"}) is not None

    assert accumulator.feed({"epoch": "0", "val/mAP_50_95": "0.4"}) is None


def test_yolo_accumulator_emits_each_epoch_once():
    accumulator = EpochAccumulator("yolo", total_epochs=5)

    assert accumulator.feed(_yolo_row()) is not None
    assert accumulator.feed(_yolo_row()) is None


def test_accumulator_flushes_incomplete_epochs():
    accumulator = EpochAccumulator("rfdetr", total_epochs=5)
    accumulator.feed({"epoch": "0", "train/loss": "2.0"})

    flushed = accumulator.flush()

    assert [metrics.epoch for metrics in flushed] == [1]
    assert flushed[0].train_loss == 2.0


# --- Eventraden över processgränsen (AC 4) ---


def test_event_line_round_trips():
    metrics = EpochMetrics(epoch=3, total_epochs=10, train_loss=1.25, map50_95=0.4)
    line = f"{EPOCH_MARKER}{json.dumps(metrics.as_dict())}"

    parsed = parse_event_line(line)

    assert parsed == metrics


def test_event_line_ignores_other_output():
    assert parse_event_line("Epok 1/10") is None
    assert parse_event_line(f"{EPOCH_MARKER}inte json") is None


def test_summary_is_readable():
    metrics = EpochMetrics(epoch=2, total_epochs=4, train_loss=1.5, map50=0.6)

    summary = metrics.summary()

    assert summary.startswith("Epok 2/4")
    assert "train-loss 1.5000" in summary
    assert "mAP50 0.6000" in summary
    assert "val-loss" not in summary


# --- MetricsTail ---


def test_metrics_tail_reads_only_new_rows(tmp_path):
    path = tmp_path / "results.csv"
    path.write_text(YOLO_HEADER + YOLO_ROW, encoding="utf-8")
    tail = MetricsTail(path)

    first = tail.read_new_rows()
    assert len(first) == 1
    assert first[0]["epoch"] == "1"
    assert tail.read_new_rows() == []

    with open(path, "a", encoding="utf-8") as file:
        file.write(YOLO_ROW.replace("1,12.5", "2,13.5"))
    second = tail.read_new_rows()
    assert [row["epoch"] for row in second] == ["2"]


def test_metrics_tail_waits_for_the_line_break(tmp_path):
    path = tmp_path / "results.csv"
    path.write_text(YOLO_HEADER, encoding="utf-8")
    tail = MetricsTail(path)
    assert tail.read_new_rows() == []

    with open(path, "a", encoding="utf-8") as file:
        file.write(YOLO_ROW[:20])
    assert tail.read_new_rows() == []

    with open(path, "a", encoding="utf-8") as file:
        file.write(YOLO_ROW[20:])
    rows = tail.read_new_rows()
    assert len(rows) == 1


def test_metrics_tail_restarts_when_the_file_is_rewritten(tmp_path):
    """Lightning raderar metrics.csv när en ny körning startar."""
    path = tmp_path / "metrics.csv"
    path.write_text(RFDETR_HEADER + "0,1,2.0,,,,,\n", encoding="utf-8")
    tail = MetricsTail(path)
    assert len(tail.read_new_rows()) == 1

    path.write_text(RFDETR_HEADER + "0,1,1.0,,,,\n", encoding="utf-8")

    rows = tail.read_new_rows()
    assert [row["train/loss"] for row in rows] == ["1.0"]


def test_metrics_tail_ignores_a_missing_file(tmp_path):
    assert MetricsTail(tmp_path / "saknas.csv").read_new_rows() == []


# --- Sparad epokhistorik (TASK-70) ---


def test_read_epoch_history_returns_every_yolo_epoch(tmp_path):
    path = tmp_path / "results.csv"
    path.write_text(YOLO_HEADER + YOLO_ROW + YOLO_ROW.replace("1,12.5", "2,13.5"),
                    encoding="utf-8")

    epochs = read_epoch_history(path, "yolo", 10)

    assert [metrics.epoch for metrics in epochs] == [1, 2]
    assert epochs[1].map50_95 == 0.41
    assert epochs[1].total_epochs == 10


def test_read_epoch_history_merges_rfdetr_rows(tmp_path):
    path = tmp_path / "metrics.csv"
    path.write_text(
        RFDETR_HEADER + "0,1,2.0,,,,\n" + "0,2,,1.8,,0.3,,\n", encoding="utf-8"
    )

    epochs = read_epoch_history(path, "rfdetr", 5)

    assert len(epochs) == 1
    assert epochs[0].epoch == 1
    assert epochs[0].train_loss == 2.0
    assert epochs[0].val_loss == 1.8
    assert epochs[0].map50_95 == 0.3


def test_read_epoch_history_without_file_is_empty(tmp_path):
    assert read_epoch_history(tmp_path / "saknas.csv", "yolo", 10) == []


# --- Rapportören (AC 1, 2) ---


def _wait_for(predicate, timeout_s=5.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_reporter_emits_one_event_per_yolo_epoch(tmp_path, capsys):
    path = tmp_path / "results.csv"
    path.write_text(YOLO_HEADER, encoding="utf-8")
    seen = []
    reporter = EpochReporter(path, "yolo", 2, seen.append, interval=0.01)
    reporter.start()
    try:
        with open(path, "a", encoding="utf-8") as file:
            file.write(YOLO_ROW)
        assert _wait_for(lambda: len(seen) == 1)
        with open(path, "a", encoding="utf-8") as file:
            file.write(YOLO_ROW.replace("1,12.5", "2,13.5"))
        assert _wait_for(lambda: len(seen) == 2)
    finally:
        reporter.stop()
        reporter.join(timeout=5)

    assert [metrics.epoch for metrics in seen] == [1, 2]
    lines = [line for line in capsys.readouterr().out.splitlines() if line.startswith(EPOCH_MARKER)]
    assert len(lines) == 2


def test_reporter_emits_rfdetr_epochs(tmp_path):
    path = tmp_path / "metrics.csv"
    path.write_text(RFDETR_HEADER, encoding="utf-8")
    seen = []
    reporter = EpochReporter(path, "rfdetr", 1, seen.append, interval=0.01)
    reporter.start()
    try:
        with open(path, "a", encoding="utf-8") as file:
            file.write("0,1,2.0,,,,,\n")
            file.write("0,2,,2.2,0.5,0.3,0.6,0.5\n")
        assert _wait_for(lambda: len(seen) == 1)
    finally:
        reporter.stop()
        reporter.join(timeout=5)

    assert seen[0].epoch == 1
    assert seen[0].train_loss == 2.0
    assert seen[0].map50_95 == 0.3


def test_reporter_flushes_incomplete_epochs_on_stop(tmp_path):
    path = tmp_path / "metrics.csv"
    path.write_text(RFDETR_HEADER, encoding="utf-8")
    seen = []
    reporter = EpochReporter(path, "rfdetr", 1, seen.append, interval=0.01)
    reporter.start()
    with open(path, "a", encoding="utf-8") as file:
        file.write("0,1,2.0,,,,,\n")
    time.sleep(0.1)  # rapportören hinner läsa raden men epoken är ofullständig
    reporter.stop()
    reporter.join(timeout=5)

    assert [metrics.epoch for metrics in seen] == [1]


# --- TrainingWorker (AC 4, 6, 7) ---


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


def test_worker_emits_structured_epoch_signal(qapp, tmp_path):
    payload = json.dumps(
        {"epoch": 2, "total_epochs": 5, "train_loss": 1.5, "map50_95": 0.4}
    )
    script = (
        "import sys\n"
        f"sys.stdout.write('{EPOCH_MARKER}{payload}\\n')\n"
        "sys.stdout.flush()\n"
    )
    worker = _worker(qapp, tmp_path, script)
    epochs = []
    lines = []
    results = []
    worker.epoch_metrics.connect(epochs.append)
    worker.progress.connect(lines.append)
    worker.finished_training.connect(lambda ok, msg: results.append(ok))
    worker.start()

    assert _wait_for_qt(qapp, lambda: bool(results))

    assert [metrics.epoch for metrics in epochs] == [2]
    assert epochs[0].map50_95 == 0.4
    assert any("Epok 2/5" in line for line in lines)


def test_worker_buffers_partial_lines(qapp, tmp_path):
    """Ultralytics skriver en rad i flera delar; den ska bli en loggrad (AC 7)."""
    script = (
        "import sys, time\n"
        "sys.stdout.write('epok 1/10 ')\n"
        "sys.stdout.flush()\n"
        "time.sleep(0.2)\n"
        "sys.stdout.write('loss=1.23\\n')\n"
        "sys.stdout.flush()\n"
    )
    worker = _worker(qapp, tmp_path, script)
    lines = []
    results = []
    worker.progress.connect(lines.append)
    worker.finished_training.connect(lambda ok, msg: results.append(ok))
    worker.start()

    assert _wait_for_qt(qapp, lambda: bool(results))

    assert lines == ["epok 1/10 loss=1.23"]


def test_worker_keeps_raw_output_in_the_log(qapp, tmp_path):
    script = "print('rad ett'); print('TRAINING_DONE'); print('rad tre')\n"
    worker = _worker(qapp, tmp_path, script)
    lines = []
    results = []
    worker.progress.connect(lines.append)
    worker.finished_training.connect(lambda ok, msg: results.append(ok))
    worker.start()

    assert _wait_for_qt(qapp, lambda: bool(results))

    assert lines == ["rad ett", "TRAINING_DONE", "rad tre"]


def test_command_passes_the_overfitting_guard(tmp_path):
    from xray_detector.infrastructure.training.trainer import TrainingWorker

    config = TrainConfig(
        dataset_yaml=tmp_path / "d.yaml",
        weights="yolo26n.pt",
        output_dir=tmp_path / "o",
        overfitting_guard=False,
    )
    command = TrainingWorker(config).command()

    assert command[command.index("--overfitting-guard") + 1] == "off"


# --- Träningsvyn (AC 5) ---


def test_training_view_shows_progress_and_values(qapp, tmp_path):
    from PySide6.QtCore import QSettings

    from xray_detector.application.dataset_service import DatasetService
    from xray_detector.domain.config import AppConfig
    from xray_detector.ui.training_view import TrainingView

    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    view = TrainingView(
        config,
        DatasetService(config.dataset_dir),
        QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat),
    )

    view._on_epoch_metrics(
        EpochMetrics(epoch=3, total_epochs=10, train_loss=1.5, map50_95=0.4)
    )

    assert view.progress_bar.maximum() == 10
    assert view.progress_bar.value() == 3
    assert view.progress_bar.format() == "Epok %v/%m"
    assert "Epok 3/10" in view.epoch_label.text()
    assert "mAP50-95 0.4000" in view.epoch_label.text()


def test_worker_finds_the_event_after_a_progress_bar(qapp, tmp_path):
    """tqdm skriver sin rad utan radbrytning, så eventet kan hamna mitt i (AC 7)."""
    payload = json.dumps({"epoch": 1, "total_epochs": 2, "train_loss": 1.0})
    script = (
        "import sys\n"
        "sys.stdout.write(chr(13) + '  1/2  2.2it/s')\n"
        f"sys.stdout.write('{EPOCH_MARKER}{payload}' + chr(10))\n"
        "sys.stdout.flush()\n"
    )
    worker = _worker(qapp, tmp_path, script)
    epochs = []
    lines = []
    results = []
    worker.epoch_metrics.connect(epochs.append)
    worker.progress.connect(lines.append)
    worker.finished_training.connect(lambda ok, msg: results.append(ok))
    worker.start()

    assert _wait_for_qt(qapp, lambda: bool(results))

    assert [metrics.epoch for metrics in epochs] == [1]
    assert "  1/2  2.2it/s" in lines
    assert any(line.startswith("Epok 1/2") for line in lines)
