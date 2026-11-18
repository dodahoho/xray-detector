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
