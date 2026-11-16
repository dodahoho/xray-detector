"""Utvärdering av en tränad modell (TASK-95): mAP, falsklarm och rapporten."""

import json
from pathlib import Path

import numpy as np

from xray_detector.application.evaluation import (
    available_splits,
    default_split,
    evaluate_run,
    load_evaluation,
    save_evaluation,
    subset_images,
    summary_text,
    view_labels,
)
from xray_detector.application.training_history import TrainingRun
from xray_detector.domain.detection import Detection
from xray_detector.infrastructure.training.metrics import (
    Prediction,
    Target,
    false_alarms_per_image,
    iou_matrix,
    match_counts,
    mean_average_precision,
    recall_at,
    threshold_for_recall,
)


def _prediction(boxes, scores, labels) -> Prediction:
    return Prediction(
        boxes=np.array(boxes, dtype=float).reshape(-1, 4),
        scores=np.array(scores, dtype=float),
        labels=np.array(labels, dtype=int),
    )


def _target(boxes, labels) -> Target:
    return Target(
        boxes=np.array(boxes, dtype=float).reshape(-1, 4),
        labels=np.array(labels, dtype=int),
    )


# --- mAP-beräkningen (AC 2, 5) ---


def test_iou_of_identical_boxes_is_one():
    assert iou_matrix(np.array([[0, 0, 10, 10]]), np.array([[0, 0, 10, 10]]))[0, 0] == 1.0


def test_iou_of_disjoint_boxes_is_zero():
    assert iou_matrix(np.array([[0, 0, 10, 10]]), np.array([[20, 20, 30, 30]]))[0, 0] == 0.0


def test_a_perfect_detection_gives_map_one():
    prediction = _prediction([[0, 0, 10, 10]], [0.9], [0])
    target = _target([[0, 0, 10, 10]], [0])

    result = mean_average_precision([prediction], [target])

    assert result["map50_95"] == 1.0
    assert result["map50"] == 1.0


def test_a_missed_object_gives_map_zero():
    prediction = _prediction([[50, 50, 60, 60]], [0.9], [0])
    target = _target([[0, 0, 10, 10]], [0])

    assert mean_average_precision([prediction], [target])["map50_95"] == 0.0


def test_half_of_the_objects_found_gives_map_half():
    prediction = _prediction([[0, 0, 10, 10]], [0.9], [0])
    target = _target([[0, 0, 10, 10], [20, 20, 30, 30]], [0, 0])

    result = mean_average_precision([prediction], [target])

    assert result["map50_95"] == 0.5


def test_a_loose_box_scores_lower_than_a_tight_one():
    target = _target([[0, 0, 10, 10]], [0])
    tight = _prediction([[0, 0, 10, 10]], [0.9], [0])
    loose = _prediction([[0, 0, 14, 10]], [0.9], [0])

    assert mean_average_precision([tight], [target])["map50_95"] > mean_average_precision(
        [loose], [target]
    )["map50_95"]


def test_map_is_averaged_over_the_classes_in_the_truth():
    prediction = _prediction([[0, 0, 10, 10], [20, 20, 30, 30]], [0.9, 0.8], [0, 1])
    target = _target([[0, 0, 10, 10], [20, 20, 30, 30]], [0, 1])

    assert mean_average_precision([prediction], [target])["map50_95"] == 1.0


def test_an_empty_truth_gives_map_zero():
    assert mean_average_precision([_prediction([[0, 0, 1, 1]], [0.9], [0])], [
        _target([], [])
    ])["map50_95"] == 0.0


# --- Falsklarm (AC 3, 5) ---


def test_match_counts_separates_hits_from_false_alarms():
    prediction = _prediction([[0, 0, 10, 10], [50, 50, 60, 60]], [0.9, 0.8], [0, 0])
    target = _target([[0, 0, 10, 10]], [0])

    assert match_counts(prediction, target, 0.5) == (1, 1, 0)


def test_a_low_confidence_prediction_is_ignored_at_a_higher_threshold():
    prediction = _prediction([[50, 50, 60, 60]], [0.2], [0])
    target = _target([[0, 0, 10, 10]], [0])

    assert match_counts(prediction, target, 0.5) == (0, 0, 1)


def test_false_alarms_per_image_counts_every_box():
    predictions = [
        _prediction([[0, 0, 1, 1], [2, 2, 3, 3]], [0.9, 0.8], [0, 0]),
        _prediction([], [], []),
    ]

    assert false_alarms_per_image(predictions, 0.5) == 1.0


def test_false_alarms_per_image_without_images_is_zero():
    assert false_alarms_per_image([], 0.5) == 0.0


def test_the_threshold_is_the_lowest_one_that_keeps_the_recall():
    prediction = _prediction([[0, 0, 10, 10]], [0.4], [0])
    target = _target([[0, 0, 10, 10]], [0])

    threshold = threshold_for_recall([prediction], [target])

    assert threshold <= 0.4
    assert recall_at([prediction], [target], threshold) == 1.0


# --- Delmängder och vyer ---


def test_the_default_split_is_held_out_for_the_family():
    assert default_split("rfdetr") == "test"
    assert default_split("yolo") == "val"
    assert available_splits("yolo") == ("val", "all")
    assert "test" in available_splits("rfdetr")


def test_the_view_comes_from_the_position_in_the_capture_group():
    images = [
        {"id": 1, "group": 1},
        {"id": 2, "group": 1},
        {"id": 3, "group": 2},
        {"id": 4, "group": 2},
    ]

    assert view_labels(images) == {1: "vy 1", 2: "vy 2", 3: "vy 1", 4: "vy 2"}


def test_the_subset_follows_the_export_split():
    images = [{"id": index, "group": index} for index in range(1, 11)]
    dataset = {"classes": ["kniv"], "images": images}

    assert len(subset_images(dataset, "all")) == 10
    assert len(subset_images(dataset, "val")) == 2
    assert len(subset_images(dataset, "test")) == 1


# --- Rapporten (AC 1, 2, 3, 4) ---


class _FakeDetector:
    """Detektor som ger en fast ruta per bild, utan modell eller GPU."""

    def __init__(self, boxes_by_name: dict[str, list[list[float]]]) -> None:
        self.boxes_by_name = boxes_by_name
        self.seen: list[str] = []

    def detect(self, frame):
        name = self._name(frame)
        self.seen.append(name)
        return [
            Detection(box[0], box[1], box[2], box[3], "kniv", 0.9)
            for box in self.boxes_by_name.get(name, [])
        ]

    @staticmethod
    def _name(frame) -> str:
        # bildens namn kodas i den första pikeln
        return str(int(frame[0, 0, 0]))


def _write_dataset(tmp_path: Path) -> tuple[dict, Path]:
    """Två bildpar: ett med kniv i båda vyerna, ett negativt par."""
    import cv2

    images_dir = tmp_path / "images"
    images_dir.mkdir(parents=True)
    images = []
    for image_id, (group, boxes) in enumerate(
        [((1, 1), [[2, 2, 12, 12]]), ((1, 1), [[2, 2, 12, 12]]), ((2, 2), []), ((2, 2), [])],
        start=1,
    ):
        name = f"img_{image_id:06d}.png"
        frame = np.full((40, 40, 3), image_id, dtype=np.uint8)
        cv2.imwrite(str(images_dir / name), frame)
        images.append(
            {
                "id": image_id,
                "file_name": name,
                "width": 40,
                "height": 40,
                "group": group,
                "annotations": [
                    {"class_name": "kniv", "bbox": [x, y, w - x, h - y]}
                    for x, y, w, h in boxes
                ],
            }
        )
    return {"classes": ["kniv"], "images": images}, images_dir


def _run(tmp_path: Path) -> TrainingRun:
    run_dir = tmp_path / "trained" / "korning"
    weights = run_dir / "yolo" / "weights" / "best.pt"
    weights.parent.mkdir(parents=True)
    weights.write_bytes(b"vikter")
    return TrainingRun(
        run_id="korning",
        run_dir=run_dir,
        family="yolo",
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
    )


def test_the_report_has_map_per_view_and_false_alarms(tmp_path):
    dataset, images_dir = _write_dataset(tmp_path)
    run = _run(tmp_path)
    detector = _FakeDetector(
        {
            "1": [[2, 2, 12, 12]],
            "2": [[2, 2, 12, 12]],
            "3": [[5, 5, 15, 15]],  # falsklarm på en negativ bild
            "4": [],
        }
    )

    report = evaluate_run(
        run,
        dataset,
        images_dir,
        split="all",
        detector_factory=lambda _run: detector,
    )

    assert report["images"] == 4
    assert report["positives"] == 2
    assert report["negatives"] == 2
    assert report["overall"]["map50_95"] == 1.0
    assert set(report["views"]) == {"vy 1", "vy 2"}
    assert report["views"]["vy 1"]["map50_95"] == 1.0
    assert report["operating_point"]["target_recall"] == 0.95
    assert report["false_alarms"]["images"] == 2
    assert report["false_alarms"]["total"] == 1
    assert report["false_alarms"]["per_image"] == 0.5


def test_a_model_that_falls_on_one_view_shows_it(tmp_path):
    dataset, images_dir = _write_dataset(tmp_path)
    run = _run(tmp_path)
    detector = _FakeDetector(
        {
            "1": [[2, 2, 12, 12]],
            "2": [],  # andra vyn hittar inget
            "3": [],
            "4": [],
        }
    )

    report = evaluate_run(
        run, dataset, images_dir, split="all", detector_factory=lambda _run: detector
    )

    assert report["views"]["vy 1"]["map50_95"] == 1.0
    assert report["views"]["vy 2"]["map50_95"] == 0.0
    assert report["overall"]["map50_95"] == 0.5


def test_the_report_is_saved_next_to_the_run(tmp_path):
    dataset, images_dir = _write_dataset(tmp_path)
    run = _run(tmp_path)
    report = evaluate_run(
        run,
        dataset,
        images_dir,
        split="all",
        detector_factory=lambda _run: _FakeDetector({}),
    )

    path = save_evaluation(run, report)

    assert path == run.run_dir / "evaluation.json"
    assert json.loads(path.read_text(encoding="utf-8"))["split"] == "all"
    assert load_evaluation(run)["images"] == 4


def test_a_run_without_a_saved_evaluation_returns_none(tmp_path):
    assert load_evaluation(_run(tmp_path)) is None


def test_the_summary_names_the_views_and_the_false_alarms(tmp_path):
    dataset, images_dir = _write_dataset(tmp_path)
    run = _run(tmp_path)
    report = evaluate_run(
        run,
        dataset,
        images_dir,
        split="all",
        detector_factory=lambda _run: _FakeDetector({"1": [[2, 2, 12, 12]]}),
    )

    text = summary_text(report)

    assert "mAP50-95" in text
    assert "vy 1" in text and "vy 2" in text
    assert "falsklarm/bild" in text
    assert "95% recall" in text


# --- Historikvyn ---


class _StubDataset:
    """Minsta dataset som historikvyn behöver för att starta en utvärdering."""

    def __init__(self, images_dir: Path) -> None:
        self.images_dir = images_dir

    def load_dataset(self) -> dict:
        return {"classes": ["kniv"], "images": []}


def _history_run(tmp_path: Path) -> TrainingRun:
    run = _run(tmp_path)
    (run.run_dir / "training_manifest.json").write_text(
        json.dumps(
            {
                "family": "yolo",
                "base_weights": "yolo26n.pt",
                "weights_relative": "yolo/weights/best.pt",
                "classes": ["kniv"],
                "epochs": 10,
                "status": "completed",
            }
        ),
        encoding="utf-8",
    )
    return run


def test_the_history_view_evaluates_the_selected_run(qapp, tmp_path, monkeypatch):
    from xray_detector.ui import training_history as history_module

    run = _history_run(tmp_path)
    calls = []

    def fake_evaluate(run, dataset, images_dir, split=None, **kwargs):
        calls.append((run.run_id, split))
        return _fake_report(run)

    monkeypatch.setattr(history_module, "evaluate_run", fake_evaluate)
    view = history_module.TrainingHistoryView(
        tmp_path / "trained", _StubDataset(tmp_path / "images")
    )
    view.table.selectRow(0)
    view.split_combo.setCurrentIndex(view.split_combo.findData("all"))

    report = view.evaluate_selected("all")

    assert calls == [("korning", "all")]
    assert report["overall"]["map50_95"] == 1.0
    assert (run.run_dir / "evaluation.json").exists()


def test_the_history_view_shows_the_saved_evaluation(qapp, tmp_path):
    from xray_detector.ui.training_history import TrainingHistoryView

    run = _history_run(tmp_path)
    save_evaluation(run, _fake_report(run))

    view = TrainingHistoryView(tmp_path / "trained")
    view.table.selectRow(0)

    assert "Utvärdering (all)" in view.evaluation_label.text()
    assert "mAP50-95 1.000" in view.evaluation_label.text()


def test_the_history_view_offers_the_splits_of_the_family(qapp, tmp_path):
    from xray_detector.ui.training_history import TrainingHistoryView

    _history_run(tmp_path)
    view = TrainingHistoryView(tmp_path / "trained")
    view.table.selectRow(0)

    splits = [view.split_combo.itemData(index) for index in range(view.split_combo.count())]

    assert splits == ["val", "all"]
    assert view.split_combo.currentData() == "val"


def test_the_evaluate_button_needs_a_dataset(qapp, tmp_path):
    from xray_detector.ui.training_history import TrainingHistoryView

    _history_run(tmp_path)
    view = TrainingHistoryView(tmp_path / "trained")
    view.table.selectRow(0)

    assert not view.evaluate_button.isEnabled()


def _fake_report(run: TrainingRun) -> dict:
    return {
        "run_id": run.run_id,
        "split": "all",
        "overall": {"map50_95": 1.0, "map50": 1.0},
        "views": {"vy 1": {"map50_95": 1.0}},
        "operating_point": {"target_recall": 0.95, "threshold": 0.01, "recall": 1.0},
        "false_alarms": {"images": 2, "total": 0, "per_image": 0.0},
    }
