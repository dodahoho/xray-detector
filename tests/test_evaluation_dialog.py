"""Jämförelsedialogen i träningsvyn (TASK-158)."""

import json
from pathlib import Path

import numpy as np

from xray_detector.application.evaluation import (
    SOURCE_DATASET,
    SOURCE_FOLDER,
    SOURCE_VIDEO,
    EvaluationSource,
)
from xray_detector.application.training_history import TrainingRun
from xray_detector.domain.detection import Detection


class _StubDataset:
    """Minsta dataset som dialogen behöver: en klass, två bilder och en katalog."""

    def __init__(self, images_dir: Path, images: list[dict] | None = None) -> None:
        self.images_dir = images_dir
        self.images = images or []

    def load_dataset(self) -> dict:
        return {"classes": ["kniv"], "images": self.images}


class _FakeDetector:
    """Detektor som ger en fast ruta per bild, utan modell eller GPU."""

    def __init__(self, boxes_by_name: dict[str, list[list[float]]]) -> None:
        self.boxes_by_name = boxes_by_name

    def detect(self, frame):
        name = str(int(frame[0, 0, 0]))
        return [
            Detection(box[0], box[1], box[2], box[3], "kniv", 0.9)
            for box in self.boxes_by_name.get(name, [])
        ]


def _write_images(folder: Path, count: int) -> None:
    import cv2

    folder.mkdir(parents=True, exist_ok=True)
    for index in range(count):
        frame = np.full((20, 20, 3), index + 1, dtype=np.uint8)
        cv2.imwrite(str(folder / f"bild_{index:03d}.png"), frame)


def _write_video(path: Path, frames: int) -> Path:
    import cv2

    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (32, 32))
    for index in range(frames):
        writer.write(np.full((32, 32, 3), index * 20, dtype=np.uint8))
    writer.release()
    return path


def _run(tmp_path: Path, run_id: str = "korning", family: str = "yolo") -> TrainingRun:
    run_dir = tmp_path / "trained" / run_id
    weights = run_dir / "yolo" / "weights" / "best.pt"
    weights.parent.mkdir(parents=True)
    weights.write_bytes(b"vikter")
    (run_dir / "training_manifest.json").write_text(
        json.dumps(
            {
                "family": family,
                "base_weights": "yolo26n.pt",
                "weights_relative": "yolo/weights/best.pt",
                "classes": ["kniv"],
                "epochs": 10,
                "status": "completed",
                "name": f"modell {run_id}",
            }
        ),
        encoding="utf-8",
    )
    return TrainingRun(
        run_id=run_id,
        run_dir=run_dir,
        family=family,
        base_weights="yolo26n.pt",
        weights=weights,
        epochs=10,
        epochs_completed=10,
        status="completed",
        started=None,
        finished=None,
        duration_seconds=None,
        metrics={},
        classes=["kniv"],
        dataset_yaml="",
        imgsz=640,
        batch=16,
        name=f"modell {run_id}",
    )


def _dialog(runs, dataset=None, images_dir=None, **kwargs):
    from xray_detector.ui.evaluation_dialog import EvaluationDialog

    return EvaluationDialog(runs, dataset, images_dir, **kwargs)


def _wait(dialog) -> None:
    dialog.wait_for_evaluation()
    # den köade finished-signalen hinner oftast fram, men inte alltid
    if dialog._task is not None:
        dialog._on_finished()


def test_the_dialog_offers_the_splits_of_the_family(qapp, tmp_path):
    dialog = _dialog([_run(tmp_path)], auto_run=False)

    splits = [dialog.split_combo.itemData(index) for index in range(dialog.split_combo.count())]

    assert splits == ["val", "all"]
    assert dialog.split_combo.currentData() == "val"


def test_an_rfdetr_run_offers_the_test_split(qapp, tmp_path):
    dialog = _dialog([_run(tmp_path, family="rfdetr")], auto_run=False)

    splits = [dialog.split_combo.itemData(index) for index in range(dialog.split_combo.count())]

    assert splits == ["test", "val", "all"]
    assert dialog.split_combo.currentData() == "test"


def test_the_dialog_runs_the_comparison_on_open(qapp, tmp_path):
    _write_images(tmp_path / "bilder", 2)
    dataset = _StubDataset(tmp_path / "bilder")
    dialog = _dialog(
        [_run(tmp_path)],
        dataset,
        tmp_path / "bilder",
        detector_factory=lambda _run: _FakeDetector({"1": [[0, 0, 5, 5]]}),
    )

    _wait(dialog)

    assert len(dialog.reports) == 1
    assert dialog.table.rowCount() == 1
    assert dialog.table.item(0, 0).text() == "modell korning"


def test_the_dataset_source_shows_the_map_columns(qapp, tmp_path):
    _write_images(tmp_path / "bilder", 2)
    images = [
        {
            "id": 1,
            "file_name": "bild_000.png",
            "group": 1,
            "annotations": [{"class_name": "kniv", "bbox": [0, 0, 5, 5]}],
        }
    ]
    dataset = _StubDataset(tmp_path / "bilder", images)
    dialog = _dialog(
        [_run(tmp_path)],
        dataset,
        tmp_path / "bilder",
        detector_factory=lambda _run: _FakeDetector({"1": [[0, 0, 5, 5]]}),
    )

    _wait(dialog)

    headers = [
        dialog.table.horizontalHeaderItem(column).text()
        for column in range(dialog.table.columnCount())
    ]
    assert headers == [
        "Modell",
        "Checkpoint",
        "Bilder",
        "mAP50-95",
        "mAP50",
        "Falsklarm/bild",
        "Tröskel",
        "Recall",
    ]
    assert not dialog.map_chart.isHidden()
    assert dialog.detection_chart.isHidden()


def test_a_folder_source_shows_the_detection_columns(qapp, tmp_path):
    _write_images(tmp_path / "bilder", 2)
    dialog = _dialog(
        [_run(tmp_path)],
        _StubDataset(tmp_path / "bilder"),
        tmp_path / "bilder",
        detector_factory=lambda _run: _FakeDetector({"1": [[0, 0, 5, 5]]}),
        auto_run=False,
    )
    dialog.source_combo.setCurrentIndex(dialog.source_combo.findData(SOURCE_FOLDER))
    dialog.path_edit.setText(str(tmp_path / "bilder"))

    dialog.run_evaluation()
    _wait(dialog)

    headers = [
        dialog.table.horizontalHeaderItem(column).text()
        for column in range(dialog.table.columnCount())
    ]
    assert headers == [
        "Modell",
        "Checkpoint",
        "Bilder",
        "Detektioner",
        "Per bild",
        "Med träff",
        "Medelkonfidens",
    ]
    assert dialog.table.item(0, 3).text() == "1"
    assert not dialog.detection_chart.isHidden()
    assert not dialog.confidence_chart.isHidden()
    assert dialog.map_chart.isHidden()
    assert dialog.stability_chart.isHidden()


def test_a_video_source_adds_the_stability_columns(qapp, tmp_path):
    path = _write_video(tmp_path / "klipp.mp4", 6)
    dialog = _dialog(
        [_run(tmp_path)],
        _StubDataset(tmp_path / "bilder"),
        tmp_path / "bilder",
        detector_factory=lambda _run: _FakeDetector({}),
        auto_run=False,
    )
    dialog.source_combo.setCurrentIndex(dialog.source_combo.findData(SOURCE_VIDEO))
    dialog.path_edit.setText(str(path))

    dialog.run_evaluation()
    _wait(dialog)

    headers = [
        dialog.table.horizontalHeaderItem(column).text()
        for column in range(dialog.table.columnCount())
    ]
    assert headers[-3:] == ["Spår", "Medellängd", "Stabila"]
    assert not dialog.stability_chart.isHidden()


def test_the_dataset_report_is_saved_next_to_the_run(qapp, tmp_path):
    _write_images(tmp_path / "bilder", 2)
    run = _run(tmp_path)
    dialog = _dialog(
        [run],
        _StubDataset(tmp_path / "bilder"),
        tmp_path / "bilder",
        detector_factory=lambda _run: _FakeDetector({}),
    )

    _wait(dialog)

    assert (run.run_dir / "evaluation.json").is_file()


def test_a_folder_report_is_not_saved_next_to_the_run(qapp, tmp_path):
    _write_images(tmp_path / "bilder", 2)
    run = _run(tmp_path)
    dialog = _dialog(
        [run],
        _StubDataset(tmp_path / "bilder"),
        tmp_path / "bilder",
        detector_factory=lambda _run: _FakeDetector({}),
        auto_run=False,
    )
    dialog.source_combo.setCurrentIndex(dialog.source_combo.findData(SOURCE_FOLDER))
    dialog.path_edit.setText(str(tmp_path / "bilder"))

    dialog.run_evaluation()
    _wait(dialog)

    assert not (run.run_dir / "evaluation.json").exists()


def test_the_run_button_needs_a_path_for_a_folder(qapp, tmp_path):
    dialog = _dialog(
        [_run(tmp_path)], _StubDataset(tmp_path / "bilder"), auto_run=False
    )

    dialog.source_combo.setCurrentIndex(dialog.source_combo.findData(SOURCE_FOLDER))

    assert not dialog.run_button.isEnabled()
    dialog.path_edit.setText(str(tmp_path / "bilder"))
    dialog._on_source_changed()
    assert dialog.run_button.isEnabled()


def test_the_split_is_hidden_for_a_folder(qapp, tmp_path):
    dialog = _dialog(
        [_run(tmp_path)], _StubDataset(tmp_path / "bilder"), auto_run=False
    )

    dialog.source_combo.setCurrentIndex(dialog.source_combo.findData(SOURCE_FOLDER))

    assert dialog.split_combo.isHidden()
    assert not dialog.path_edit.isHidden()
    assert not dialog.browse_button.isHidden()


def test_the_dialog_compares_every_selected_run(qapp, tmp_path):
    _write_images(tmp_path / "bilder", 2)
    runs = [_run(tmp_path, "forsta"), _run(tmp_path, "andra")]
    dialog = _dialog(
        runs,
        _StubDataset(tmp_path / "bilder"),
        tmp_path / "bilder",
        detector_factory=lambda _run: _FakeDetector({}),
    )

    _wait(dialog)

    assert dialog.table.rowCount() == 2
    assert [dialog.table.item(row, 0).text() for row in range(2)] == [
        "modell forsta",
        "modell andra",
    ]


def test_the_source_label_names_the_split(qapp, tmp_path):
    dialog = _dialog([_run(tmp_path)], _StubDataset(tmp_path / "bilder"), auto_run=False)
    dialog.split_combo.setCurrentIndex(dialog.split_combo.findData("all"))

    assert dialog.current_source() == EvaluationSource(kind=SOURCE_DATASET, split="all")
    assert dialog.current_source().label == "Dataset (Alla)"


def test_a_failing_evaluation_is_reported(qapp, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    from xray_detector.ui import evaluation_dialog as dialog_module

    messages: list[str] = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        staticmethod(lambda parent, title, text, *a, **k: messages.append(text)),
    )

    def broken(*_args, **_kwargs):
        raise ValueError("modellen gick inte att läsa")

    monkeypatch.setattr(dialog_module, "compare_runs", broken)
    dialog = _dialog(
        [_run(tmp_path)], _StubDataset(tmp_path / "bilder"), auto_run=False
    )

    dialog.run_evaluation()
    _wait(dialog)

    assert messages == ["modellen gick inte att läsa"]
    assert dialog.table.rowCount() == 0


# --- Eget dataset på disk (TASK-158) ---


def _write_yolo_dataset(root: Path) -> Path:
    """Ett litet YOLO-dataset: data.yaml, images/ och labels/."""
    import cv2

    from xray_detector.infrastructure.dataset_store.yolo import (
        write_data_yaml,
        write_labels,
    )

    images_dir = root / "images"
    labels_dir = root / "labels"
    images_dir.mkdir(parents=True)
    labels_dir.mkdir(parents=True)
    write_data_yaml(root / "data.yaml", ["kniv"])
    for index in (1, 2):
        name = f"bild_{index:03d}.png"
        cv2.imwrite(str(images_dir / name), np.full((40, 40, 3), index, dtype=np.uint8))
        rows = [(0, 0.25, 0.25, 0.25, 0.25)] if index == 1 else []
        write_labels(labels_dir / f"bild_{index:03d}.txt", rows)
    return root


def test_the_dataset_source_can_point_at_another_dataset(qapp, tmp_path):
    root = _write_yolo_dataset(tmp_path / "annat")
    dialog = _dialog(
        [_run(tmp_path)],
        _StubDataset(tmp_path / "bilder"),
        tmp_path / "bilder",
        detector_factory=lambda _run: _FakeDetector({"1": [[5, 5, 15, 15]]}),
        auto_run=False,
    )
    dialog.split_combo.setCurrentIndex(dialog.split_combo.findData("all"))
    dialog.path_edit.setText(str(root))

    dialog.run_evaluation()
    _wait(dialog)

    assert dialog.current_source().path == root
    assert dialog.current_source().label == "Dataset (Alla): annat"
    assert dialog.table.item(0, 2).text() == "2"
    assert dialog.table.item(0, 3).text() == "1.000"


def test_an_empty_dataset_path_means_the_applications_own_dataset(qapp, tmp_path):
    dialog = _dialog(
        [_run(tmp_path)], _StubDataset(tmp_path / "bilder"), auto_run=False
    )

    assert dialog.current_source().path is None
    assert dialog.current_source().label == "Dataset (Val)"


def test_the_dataset_source_needs_a_dataset_or_a_path(qapp, tmp_path):
    dialog = _dialog([_run(tmp_path)], None, auto_run=False)

    assert not dialog.run_button.isEnabled()

    dialog.path_edit.setText(str(tmp_path / "annat"))

    assert dialog.run_button.isEnabled()


# --- Detektionen släpper GPU:n (TASK-158) ---


def test_the_dialog_reports_when_the_evaluation_starts_and_ends(qapp, tmp_path):
    _write_images(tmp_path / "bilder", 2)
    dialog = _dialog(
        [_run(tmp_path)],
        _StubDataset(tmp_path / "bilder"),
        tmp_path / "bilder",
        detector_factory=lambda _run: _FakeDetector({}),
        auto_run=False,
    )
    events: list[str] = []
    dialog.evaluation_started.connect(lambda: events.append("start"))
    dialog.evaluation_finished.connect(lambda: events.append("klar"))

    dialog.run_evaluation()
    _wait(dialog)

    assert events == ["start", "klar"]


def test_the_history_view_passes_the_evaluation_signals_on(qapp, tmp_path, monkeypatch):
    from PySide6.QtCore import QObject, Qt, Signal

    from xray_detector.ui import training_history as history_module

    _run(tmp_path)
    view = history_module.TrainingHistoryView(
        tmp_path / "trained", _StubDataset(tmp_path / "bilder")
    )

    class _FakeDialog(QObject):
        finished = Signal(int)
        evaluation_started = Signal()
        evaluation_finished = Signal()

        def __init__(self, *_args, **_kwargs) -> None:
            super().__init__()

        def open(self) -> None:
            pass

    monkeypatch.setattr(history_module, "EvaluationDialog", _FakeDialog)
    view.table.item(0, history_module.CHECK_COLUMN).setCheckState(
        Qt.CheckState.Checked
    )
    events: list[str] = []
    view.evaluation_started.connect(lambda: events.append("start"))
    view.evaluation_finished.connect(lambda: events.append("klar"))

    view.evaluate_button.click()
    view.dialog.evaluation_started.emit()
    view.dialog.evaluation_finished.emit()

    assert events == ["start", "klar"]


def test_the_evaluate_button_waits_while_training_runs(qapp, tmp_path):
    from PySide6.QtCore import Qt

    from xray_detector.ui.training_history import CHECK_COLUMN, TrainingHistoryView

    _run(tmp_path)
    view = TrainingHistoryView(tmp_path / "trained", _StubDataset(tmp_path / "bilder"))
    view.table.item(0, CHECK_COLUMN).setCheckState(Qt.CheckState.Checked)
    assert view.evaluate_button.isEnabled()

    view.set_training_active(True)

    assert not view.evaluate_button.isEnabled()

    view.set_training_active(False)

    assert view.evaluate_button.isEnabled()


def test_the_main_window_pauses_the_detection_during_the_evaluation(
    qapp, tmp_path, monkeypatch
):
    from xray_detector.domain.config import AppConfig
    from xray_detector.ui.main_window import MainWindow

    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    window = MainWindow(config)
    calls: list[str] = []
    monkeypatch.setattr(
        window.detection_view, "pause_detection", lambda: calls.append("paus")
    )
    monkeypatch.setattr(
        window.detection_view, "resume_detection", lambda: calls.append("igång")
    )

    window.training_view.history.evaluation_started.emit()
    window.training_view.history.evaluation_finished.emit()

    assert calls == ["paus", "igång"]
