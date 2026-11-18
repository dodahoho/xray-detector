"""Tidigare träningar och export av vald modell (TASK-59)."""

import json
from datetime import datetime
from pathlib import Path

import pytest
from PySide6.QtWidgets import QMessageBox

from xray_detector.application.training_history import (
    TrainingRun,
    delete_run,
    export_run,
    run_epochs,
    training_runs,
)


def _write_run(
    trained_dir: Path,
    run: str,
    *,
    family: str = "yolo",
    base_weights: str = "yolo26n.pt",
    weights_relative: str = "yolo/weights/best.pt",
    started: str = "2026-11-12T09:00:00+00:00",
    finished: str = "2026-11-12T09:12:30+00:00",
    duration_seconds: float | None = 750.0,
    epochs: int = 10,
    epochs_completed: int = 10,
    status: str = "completed",
    metrics: dict | None = None,
    name: str = "",
) -> Path:
    run_dir = trained_dir / run
    weights = run_dir / weights_relative
    weights.parent.mkdir(parents=True, exist_ok=True)
    weights.write_bytes(b"vikter")
    manifest = {
        "family": family,
        "base_weights": base_weights,
        "weights_relative": weights_relative,
        "classes": ["kniv", "pistol"],
        "dataset_yaml": "C:/data/exports/yolo/data.yaml",
        "epochs": epochs,
        "epochs_completed": epochs_completed,
        "imgsz": 640,
        "batch": 16,
        "status": status,
        "started": started,
        "finished": finished,
        "duration_seconds": duration_seconds,
        "metrics": metrics if metrics is not None else {"map50_95": 0.412},
    }
    # äldre manifest saknar namnet helt, så det skrivs bara när det finns
    if name:
        manifest["name"] = name
    (run_dir / "training_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    return run_dir


# --- Listning (AC 1, 2) ---


def test_runs_are_listed_newest_first(tmp_path):
    _write_run(tmp_path, "2026-11-11_120000", started="2026-11-11T12:00:00+00:00")
    _write_run(tmp_path, "2026-11-12_090000", started="2026-11-12T09:00:00+00:00")

    runs = training_runs(tmp_path)

    assert [run.run_id for run in runs] == ["2026-11-12_090000", "2026-11-11_120000"]


def test_run_describes_the_training(tmp_path):
    _write_run(tmp_path, "korning")

    run = training_runs(tmp_path)[0]

    assert run.family == "yolo"
    assert run.base_weights == "yolo26n.pt"
    assert run.epochs == 10
    assert run.status_label == "Klar"
    assert run.map50_95_text == "0.412"
    assert run.weights.exists()


def test_details_show_the_important_parameters(tmp_path):
    _write_run(tmp_path, "korning")

    details = training_runs(tmp_path)[0].details

    assert "Dataset: C:/data/exports/yolo/data.yaml" in details
    assert "Bildstorlek (längsta sidan): 640" in details
    assert "Batch: 16" in details
    assert "mAP50-95: 0.412" in details
    assert "kniv, pistol" in details


def test_runs_without_weights_are_skipped(tmp_path):
    run_dir = tmp_path / "trasig"
    run_dir.mkdir()
    (run_dir / "training_manifest.json").write_text(
        json.dumps({"weights_relative": "saknas/best.pt"}), encoding="utf-8"
    )

    assert training_runs(tmp_path) == []


def test_broken_manifest_is_skipped(tmp_path):
    run_dir = tmp_path / "trasig"
    run_dir.mkdir()
    (run_dir / "training_manifest.json").write_text("{inte json", encoding="utf-8")

    assert training_runs(tmp_path) == []


# --- Tidsåtgång (AC 1) ---


def test_duration_comes_from_the_manifest(tmp_path):
    _write_run(tmp_path, "korning", duration_seconds=750.0)

    assert training_runs(tmp_path)[0].duration_text == "12 min 30 s"


def test_duration_is_computed_from_the_timestamps(tmp_path):
    _write_run(
        tmp_path,
        "korning",
        duration_seconds=None,
        started="2026-11-12T09:00:00+00:00",
        finished="2026-11-12T10:30:00+00:00",
    )

    assert training_runs(tmp_path)[0].duration_text == "1 h 30 min"


def test_missing_duration_is_shown_as_dash(tmp_path):
    _write_run(
        tmp_path, "korning", duration_seconds=None, started=None, finished=None
    )

    assert training_runs(tmp_path)[0].duration_text == "-"


def test_aborted_run_shows_completed_epochs(tmp_path):
    _write_run(
        tmp_path, "korning", status="aborted", epochs=10, epochs_completed=4
    )

    run = training_runs(tmp_path)[0]

    assert run.epochs_text == "4/10"
    assert run.status_label == "Avbruten"


# --- Export (AC 4, 5) ---


def test_export_copies_weights_and_manifest(tmp_path):
    trained = tmp_path / "trained"
    _write_run(trained, "korning")
    run = training_runs(trained)[0]
    target = tmp_path / "export"

    exported = export_run(run, target)

    assert exported == target / "korning"
    assert (exported / "best.pt").read_bytes() == b"vikter"
    assert (exported / "training_manifest.json").is_file()


def test_export_keeps_the_rfdetr_format(tmp_path):
    trained = tmp_path / "trained"
    _write_run(
        trained,
        "korning",
        family="rfdetr",
        base_weights="rfdetr-small",
        weights_relative="rfdetr/checkpoint_best_total.pth",
    )
    run = training_runs(trained)[0]

    exported = export_run(run, tmp_path / "export")

    assert (exported / "checkpoint_best_total.pth").is_file()


def test_export_flattens_nested_run_ids(tmp_path):
    trained = tmp_path / "trained"
    _write_run(trained, "2026-11-12/korning")
    run = training_runs(trained)[0]

    exported = export_run(run, tmp_path / "export")

    assert exported.name == "2026-11-12_korning"


# --- Sparad epokhistorik (TASK-70) ---


def test_run_epochs_reads_the_saved_metrics(tmp_path):
    run_dir = _write_run(tmp_path, "korning")
    (run_dir / "yolo" / "results.csv").write_text(
        "epoch,train/box_loss,metrics/mAP50-95(B)\n1,2.0,0.2\n2,1.5,0.35\n",
        encoding="utf-8",
    )

    epochs = run_epochs(training_runs(tmp_path)[0])

    assert [metrics.epoch for metrics in epochs] == [1, 2]
    assert epochs[-1].train_loss == 1.5
    assert epochs[-1].map50_95 == 0.35


def test_run_epochs_reads_the_rfdetr_metrics(tmp_path):
    run_dir = _write_run(
        tmp_path,
        "korning",
        family="rfdetr",
        base_weights="rfdetr-small",
        weights_relative="rfdetr/checkpoint_best_total.pth",
    )
    (run_dir / "rfdetr" / "metrics.csv").write_text(
        "epoch,train/loss,val/loss,val/mAP_50_95\n0,2.0,,,\n0,,1.8,0.3\n",
        encoding="utf-8",
    )

    epochs = run_epochs(training_runs(tmp_path)[0])

    assert len(epochs) == 1
    assert epochs[0].train_loss == 2.0
    assert epochs[0].map50_95 == 0.3


def test_run_epochs_without_metrics_file_is_empty(tmp_path):
    _write_run(tmp_path, "korning")

    assert run_epochs(training_runs(tmp_path)[0]) == []


# --- Träningsvyn (AC 1, 3, 6, 7) ---


def _history_view(qapp, trained_dir):
    from xray_detector.ui.training_history import TrainingHistoryView

    return TrainingHistoryView(trained_dir)


def _local_text(value: str) -> str:
    """Samma omräkning som vyn gör, så testet går i vilken tidszon som helst."""
    return datetime.fromisoformat(value).astimezone().strftime("%Y-%m-%d %H:%M")


def test_history_view_lists_the_runs(qapp, tmp_path):
    from xray_detector.ui.training_history import COLUMNS

    _write_run(tmp_path, "2026-11-12_090000")
    _write_run(tmp_path, "2026-11-11_120000", started="2026-11-11T12:00:00+00:00")

    view = _history_view(qapp, tmp_path)

    assert view.table.rowCount() == 2
    assert view.table.item(0, COLUMNS.index("Datum")).text() == _local_text(
        "2026-11-12T09:00:00+00:00"
    )
    assert view.table.item(0, COLUMNS.index("Status")).text() == "Klar"
    assert view.table.item(0, COLUMNS.index("Tid")).text() == "12 min 30 s"


def test_the_columns_name_the_run_its_model_and_its_checkpoint(qapp, tmp_path):
    """Kolumnerna heter Datum, Modellnamn och Checkpoint (TASK-157)."""
    from xray_detector.ui.training_history import COLUMNS

    _write_run(tmp_path, "korning", name="YOLO26 large 2026-11-12")

    view = _history_view(qapp, tmp_path)

    assert COLUMNS == (
        "Val",
        "Datum",
        "Modellnamn",
        "Checkpoint",
        "Epoker",
        "Tid",
        "mAP50-95",
        "Status",
        "Notering",
    )
    assert view.table.item(0, COLUMNS.index("Modellnamn")).text() == (
        "YOLO26 large 2026-11-12"
    )
    assert view.table.item(0, COLUMNS.index("Checkpoint")).text() == "yolo26n"


def test_a_manifest_without_a_name_shows_a_dash(qapp, tmp_path):
    """Manifest som skrevs innan namnet fanns har inget modellnamn (TASK-157)."""
    from xray_detector.ui.training_history import COLUMNS

    _write_run(tmp_path, "korning")

    view = _history_view(qapp, tmp_path)

    assert view.table.item(0, COLUMNS.index("Modellnamn")).text() == "-"


def test_a_run_without_a_start_time_shows_a_dash(qapp, tmp_path):
    from xray_detector.ui.training_history import COLUMNS

    _write_run(tmp_path, "korning", started=None, finished=None, duration_seconds=None)

    view = _history_view(qapp, tmp_path)

    assert view.table.item(0, COLUMNS.index("Datum")).text() == "-"


def test_the_details_line_uses_the_new_terms(qapp, tmp_path):
    """Raden under tabellen talar om checkpoint och notering (TASK-157)."""
    _write_run(tmp_path, "korning")
    view = _history_view(qapp, tmp_path)

    view.table.selectRow(0)

    assert "Checkpoint: yolo26n" in view.details.text()
    assert "Notering:" in view.details.text()
    assert "Basmodell:" not in view.details.text()
    assert "Dom:" not in view.details.text()


# --- Markering för jämförelsen (TASK-158) ---


def test_every_row_starts_unchecked(qapp, tmp_path):
    from PySide6.QtCore import Qt

    from xray_detector.ui.training_history import CHECK_COLUMN

    _write_run(tmp_path, "korning")

    view = _history_view(qapp, tmp_path)

    assert view.table.item(0, CHECK_COLUMN).checkState() == Qt.CheckState.Unchecked
    assert view.checked_runs() == []


def test_a_checked_row_is_part_of_the_comparison(qapp, tmp_path):
    from PySide6.QtCore import Qt

    from xray_detector.ui.training_history import CHECK_COLUMN

    _write_run(tmp_path, "korning")

    view = _history_view(qapp, tmp_path)
    view.table.item(0, CHECK_COLUMN).setCheckState(Qt.CheckState.Checked)

    assert [run.run_id for run in view.checked_runs()] == ["korning"]


def test_select_all_marks_and_clears_every_row(qapp, tmp_path):
    from PySide6.QtCore import Qt

    _write_run(tmp_path, "2026-11-11_120000", started="2026-11-11T12:00:00+00:00")
    _write_run(tmp_path, "2026-11-12_090000", started="2026-11-12T09:00:00+00:00")
    view = _history_view(qapp, tmp_path)

    view.select_all.setChecked(True)

    assert len(view.checked_runs()) == 2
    assert view.select_all.checkState() == Qt.CheckState.Checked

    view.select_all.setChecked(False)

    assert view.checked_runs() == []


def test_select_all_shows_a_partial_state(qapp, tmp_path):
    from PySide6.QtCore import Qt

    from xray_detector.ui.training_history import CHECK_COLUMN

    _write_run(tmp_path, "2026-11-11_120000", started="2026-11-11T12:00:00+00:00")
    _write_run(tmp_path, "2026-11-12_090000", started="2026-11-12T09:00:00+00:00")
    view = _history_view(qapp, tmp_path)

    view.table.item(0, CHECK_COLUMN).setCheckState(Qt.CheckState.Checked)

    assert view.select_all.checkState() == Qt.CheckState.PartiallyChecked


def test_a_checked_row_survives_a_refresh(qapp, tmp_path):
    from PySide6.QtCore import Qt

    from xray_detector.ui.training_history import CHECK_COLUMN

    _write_run(tmp_path, "korning")
    view = _history_view(qapp, tmp_path)
    view.table.item(0, CHECK_COLUMN).setCheckState(Qt.CheckState.Checked)

    view.refresh()

    assert view.table.item(0, CHECK_COLUMN).checkState() == Qt.CheckState.Checked
    assert [run.run_id for run in view.checked_runs()] == ["korning"]


def test_the_evaluate_button_needs_a_checked_row(qapp, tmp_path):
    from PySide6.QtCore import Qt

    from xray_detector.ui.training_history import CHECK_COLUMN

    _write_run(tmp_path, "korning")
    view = _history_view(qapp, tmp_path)

    assert not view.evaluate_button.isEnabled()

    view.table.item(0, CHECK_COLUMN).setCheckState(Qt.CheckState.Checked)

    assert not view.evaluate_button.isEnabled()


def test_wait_for_evaluation_waits_for_the_open_dialog(qapp, tmp_path):
    """Stängningen väntar in en pågående utvärdering i dialogen (TASK-158)."""
    _write_run(tmp_path, "korning")
    view = _history_view(qapp, tmp_path)
    waited: list[int] = []

    class _Dialog:
        def wait_for_evaluation(self, timeout_ms: int = 60000) -> None:
            waited.append(timeout_ms)

    view.dialog = _Dialog()

    view.wait_for_evaluation(1234)

    assert waited == [1234]


def test_export_button_is_disabled_without_a_selection(qapp, tmp_path):
    _write_run(tmp_path, "korning")

    view = _history_view(qapp, tmp_path)

    assert view.selected_run() is None
    assert not view.export_button.isEnabled()
    assert view.export_selected(tmp_path / "export") is None


def test_selecting_a_run_enables_the_export(qapp, tmp_path):
    _write_run(tmp_path, "korning")
    view = _history_view(qapp, tmp_path)

    view.table.selectRow(0)

    assert view.selected_run().run_id == "korning"
    assert view.export_button.isEnabled()
    assert "Dataset:" in view.details.text()


def test_export_selected_writes_the_model(qapp, tmp_path):
    _write_run(tmp_path, "korning")
    view = _history_view(qapp, tmp_path)
    view.table.selectRow(0)

    exported = view.export_selected(tmp_path / "export")

    assert exported == tmp_path / "export" / "korning"
    assert (exported / "best.pt").is_file()


def test_history_view_refreshes_after_training(qapp, tmp_path):
    from PySide6.QtCore import QSettings

    from xray_detector.domain.config import AppConfig
    from xray_detector.infrastructure.dataset_store.store import DatasetStore
    from xray_detector.ui.training_view import TrainingView

    config = AppConfig()
    config.data_dir = tmp_path / "data"
    config.models_dir = tmp_path / "models"
    config.ensure_dirs()
    view = TrainingView(
        config,
        DatasetStore(config.dataset_dir),
        QSettings(str(config.data_dir / "s.ini"), QSettings.Format.IniFormat),
    )
    assert view.history.table.rowCount() == 0

    _write_run(config.trained_dir, "korning")
    view._on_finished(True, "Träning avslutad (kod 0)")

    assert view.history.table.rowCount() == 1


def test_history_is_a_tab_next_to_the_log(qapp, tmp_path):
    from PySide6.QtCore import QSettings

    from xray_detector.domain.config import AppConfig
    from xray_detector.infrastructure.dataset_store.store import DatasetStore
    from xray_detector.ui.training_view import TrainingView

    config = AppConfig()
    config.data_dir = tmp_path / "data"
    config.models_dir = tmp_path / "models"
    config.ensure_dirs()
    view = TrainingView(
        config,
        DatasetStore(config.dataset_dir),
        QSettings(str(config.data_dir / "s.ini"), QSettings.Format.IniFormat),
    )

    titles = [view.bottom_tabs.tabText(i) for i in range(view.bottom_tabs.count())]
    assert titles == ["Logg", "Tidigare träningar"]
    assert view.bottom_tabs.widget(0) is view.log
    assert view.bottom_tabs.widget(1) is view.history


def test_run_details_are_readable_for_a_manual_run(tmp_path):
    """En körning utan metrics ska ändå gå att visa."""
    run = TrainingRun(
        run_id="korning",
        run_dir=tmp_path,
        family="yolo",
        base_weights="yolo26n.pt",
        weights=tmp_path / "best.pt",
        epochs=0,
        epochs_completed=0,
        status="running",
        started=None,
        finished=None,
        duration_seconds=None,
        metrics={},
        classes=[],
        dataset_yaml="",
        imgsz=None,
        batch=None,
    )

    assert run.map50_95_text == "-"
    assert run.status_label == "Pågår"
    assert "Bildstorlek (längsta sidan): -" in run.details


# --- Borttagning av en träning (TASK-119) ---


def test_delete_run_removes_the_run_directory(tmp_path):
    run_dir = _write_run(tmp_path, "korning")
    (run_dir / "evaluation.json").write_text("{}", encoding="utf-8")

    delete_run(tmp_path, "korning")

    assert not run_dir.exists()
    assert training_runs(tmp_path) == []


def test_delete_run_keeps_the_other_runs(tmp_path):
    _write_run(tmp_path, "2026-11-11_120000", started="2026-11-11T12:00:00+00:00")
    _write_run(tmp_path, "2026-11-12_090000", started="2026-11-12T09:00:00+00:00")

    delete_run(tmp_path, "2026-11-12_090000")

    assert [run.run_id for run in training_runs(tmp_path)] == ["2026-11-11_120000"]


def test_delete_run_refuses_a_path_outside_the_trained_dir(tmp_path):
    trained = tmp_path / "trained"
    trained.mkdir()
    outside = tmp_path / "annat"
    outside.mkdir()

    with pytest.raises(ValueError):
        delete_run(trained, "../annat")

    assert outside.is_dir()


def test_delete_button_is_disabled_without_a_selection(qapp, tmp_path):
    _write_run(tmp_path, "korning")

    view = _history_view(qapp, tmp_path)

    assert not view.delete_button.isEnabled()
    assert view.delete_selected() is False


def test_delete_selected_removes_the_run_and_its_files(qapp, tmp_path):
    run_dir = _write_run(tmp_path, "korning")
    view = _history_view(qapp, tmp_path)
    view.table.selectRow(0)

    assert view.delete_selected() is True

    assert not run_dir.exists()
    assert view.table.rowCount() == 0
    assert view.selected_run() is None


def test_deleting_a_run_emits_run_deleted(qapp, tmp_path):
    _write_run(tmp_path, "korning")
    view = _history_view(qapp, tmp_path)
    view.table.selectRow(0)
    emitted = []
    view.run_deleted.connect(lambda: emitted.append(True))

    view.delete_selected()

    assert emitted == [True]


def test_delete_button_asks_before_removing(qapp, tmp_path, monkeypatch):
    run_dir = _write_run(tmp_path, "korning")
    view = _history_view(qapp, tmp_path)
    view.table.selectRow(0)
    messages: list[str] = []

    def warning(parent, title, text, *args, **kwargs):
        messages.append(text)
        return QMessageBox.StandardButton.Cancel

    monkeypatch.setattr(QMessageBox, "warning", staticmethod(warning))

    view.delete_button.click()

    assert run_dir.is_dir()
    assert "korning" in messages[0]


def test_delete_button_removes_the_run_when_confirmed(qapp, tmp_path, monkeypatch):
    run_dir = _write_run(tmp_path, "korning")
    view = _history_view(qapp, tmp_path)
    view.table.selectRow(0)
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        staticmethod(lambda *args, **kwargs: QMessageBox.StandardButton.Ok),
    )

    view.delete_button.click()

    assert not run_dir.exists()
    assert view.table.rowCount() == 0


def test_running_training_cannot_be_deleted(qapp, tmp_path):
    from xray_detector.ui.training_history import TrainingHistoryView

    run_dir = _write_run(tmp_path, "korning", status="running")
    view = TrainingHistoryView(tmp_path, active_run_dir=lambda: run_dir)
    view.table.selectRow(0)

    assert not view.delete_button.isEnabled()
    assert view.delete_selected() is False
    assert run_dir.is_dir()
