"""Utvärdering av en tränad modell (TASK-95): mAP, falsklarm och rapporten."""

import json
from pathlib import Path

import numpy as np
import pytest

from xray_detector.application.evaluation import (
    SOURCE_DATASET,
    SOURCE_FOLDER,
    EvaluationSource,
    available_splits,
    compare_runs,
    default_split,
    evaluate_detections,
    evaluate_run,
    evaluate_source,
    folder_frames,
    load_evaluation,
    save_evaluation,
    subset_images,
    summary_text,
    video_frames,
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
    stability_summary,
    threshold_for_recall,
    track_lengths,
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

    def __init__(
        self, boxes_by_name: dict[str, list[list[float]]], confidence: float = 0.9
    ) -> None:
        self.boxes_by_name = boxes_by_name
        self.confidence = confidence
        self.seen: list[str] = []

    def detect(self, frame):
        name = self._name(frame)
        self.seen.append(name)
        return [
            Detection(box[0], box[1], box[2], box[3], "kniv", self.confidence)
            for box in self.boxes_by_name.get(name, [])
        ]

    @staticmethod
    def _name(frame) -> str:
        # bildens namn kodas i den första pikeln
        return str(int(frame[0, 0, 0]))


class _FixedDetector:
    """Detektor som ger samma rutor i varje bildruta, oberoende av innehållet."""

    def __init__(self, boxes: list[list[float]]) -> None:
        self.boxes = boxes

    def detect(self, _frame):
        return [Detection(box[0], box[1], box[2], box[3], "kniv", 0.9) for box in self.boxes]


class _AlternatingDetector:
    """Larmar varannan bildruta, så varje spår blir en ruta långt."""

    def __init__(self) -> None:
        self.calls = 0

    def detect(self, _frame):
        self.calls += 1
        if self.calls % 2:
            return [Detection(0, 0, 5, 5, "kniv", 0.9)]
        return []


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


def _run(tmp_path: Path, run_id: str = "korning") -> TrainingRun:
    run_dir = tmp_path / "trained" / run_id
    weights = run_dir / "yolo" / "weights" / "best.pt"
    weights.parent.mkdir(parents=True)
    weights.write_bytes(b"vikter")
    return TrainingRun(
        run_id=run_id,
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


# --- Källor utan annoteringar (TASK-158) ---


def test_a_track_that_stays_in_place_counts_every_frame():
    frames = [_prediction([[0, 0, 10, 10]], [0.9], [0]) for _ in range(3)]

    assert track_lengths(frames) == [3]


def test_a_gap_breaks_the_track():
    frames = [
        _prediction([[0, 0, 10, 10]], [0.9], [0]),
        _prediction([], [], []),
        _prediction([[0, 0, 10, 10]], [0.9], [0]),
    ]

    assert track_lengths(frames) == [1, 1]


def test_a_track_does_not_jump_between_classes():
    frames = [
        _prediction([[0, 0, 10, 10]], [0.9], [0]),
        _prediction([[0, 0, 10, 10]], [0.9], [1]),
    ]

    assert track_lengths(frames) == [1, 1]


def test_two_objects_that_move_get_one_track_each():
    frames = [
        _prediction([[0, 0, 10, 10], [50, 50, 60, 60]], [0.9, 0.8], [0, 0]),
        _prediction([[1, 0, 11, 10], [51, 50, 61, 60]], [0.9, 0.8], [0, 0]),
    ]

    assert track_lengths(frames) == [2, 2]


def test_stability_counts_the_share_of_stable_tracks():
    summary = stability_summary([3, 3, 1])

    assert summary["tracks"] == 3
    assert summary["mean_length"] == pytest.approx(7 / 3)
    assert summary["stable_share"] == pytest.approx(2 / 3)
    assert summary["single_frame"] == 1


def test_stability_without_tracks_is_zero():
    assert stability_summary([]) == {
        "tracks": 0,
        "mean_length": 0.0,
        "stable_share": 0.0,
        "single_frame": 0,
    }


def _write_images(folder: Path, count: int) -> None:
    """Bilder vars första pixel är bildens nummer, så detektorn kan känna igen dem."""
    import cv2

    folder.mkdir(parents=True, exist_ok=True)
    for index in range(count):
        frame = np.full((20, 20, 3), index + 1, dtype=np.uint8)
        cv2.imwrite(str(folder / f"bild_{index:03d}.png"), frame)


def _write_video(path: Path, frames: int) -> Path:
    import cv2

    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (32, 32)
    )
    for index in range(frames):
        writer.write(np.full((32, 32, 3), index * 20, dtype=np.uint8))
    writer.release()
    return path


def test_a_folder_yields_its_images_in_name_order(tmp_path):
    _write_images(tmp_path / "bilder", 3)
    (tmp_path / "bilder" / "anteckning.txt").write_text("inte en bild", encoding="utf-8")

    names = [name for name, _frame, _image in folder_frames(tmp_path / "bilder")]

    assert names == ["bild_000.png", "bild_001.png", "bild_002.png"]


def test_a_video_yields_every_stride_frame(tmp_path):
    path = _write_video(tmp_path / "klipp.mp4", 10)

    names = [name for name, _frame, _image in video_frames(path, stride=5)]

    assert names == ["ruta 0", "ruta 5"]


def test_a_missing_video_is_an_error(tmp_path):
    with pytest.raises(ValueError):
        list(video_frames(tmp_path / "saknas.mp4"))


def test_detections_are_counted_per_image_and_class(tmp_path):
    _write_images(tmp_path / "bilder", 3)
    detector = _FakeDetector(
        {"1": [[0, 0, 5, 5]], "2": [[0, 0, 5, 5], [6, 6, 9, 9]], "3": []}
    )

    report = evaluate_detections(
        _run(tmp_path),
        folder_frames(tmp_path / "bilder"),
        detector_factory=lambda _run: detector,
    )

    assert report["images"] == 3
    assert report["detections"]["total"] == 3
    assert report["detections"]["per_image"] == 1.0
    assert report["detections"]["with_detection_share"] == pytest.approx(2 / 3)
    assert report["detections"]["per_class"] == {"kniv": 3}
    assert report["detections"]["mean_confidence"] == pytest.approx(0.9)
    assert "stability" not in report


def test_the_confidence_histogram_puts_the_scores_in_their_bin(tmp_path):
    _write_images(tmp_path / "bilder", 2)
    detector = _FakeDetector({"1": [[0, 0, 5, 5]], "2": [[0, 0, 5, 5]]})

    report = evaluate_detections(
        _run(tmp_path),
        folder_frames(tmp_path / "bilder"),
        detector_factory=lambda _run: detector,
    )

    histogram = report["detections"]["histogram"]
    assert sum(histogram) == 2
    assert histogram[9] == 2


def test_detections_below_the_threshold_are_not_counted(tmp_path):
    _write_images(tmp_path / "bilder", 2)
    detector = _FakeDetector(
        {"1": [[0, 0, 5, 5]], "2": [[0, 0, 5, 5]]}, confidence=0.2
    )

    report = evaluate_detections(
        _run(tmp_path),
        folder_frames(tmp_path / "bilder"),
        detector_factory=lambda _run: detector,
    )

    assert report["detections"]["total"] == 0
    assert report["detections"]["with_detection_share"] == 0.0
    assert report["detections"]["mean_confidence"] == 0.0


def test_a_video_report_measures_how_long_a_track_survives(tmp_path):
    path = _write_video(tmp_path / "klipp.mp4", 6)

    report = evaluate_detections(
        _run(tmp_path),
        video_frames(path, stride=1),
        detector_factory=lambda _run: _FixedDetector([[0, 0, 5, 5]]),
        temporal=True,
    )

    assert report["images"] == 6
    assert report["stability"]["tracks"] == 1
    assert report["stability"]["mean_length"] == 6.0
    assert report["stability"]["stable_share"] == 1.0


def test_a_flickering_detector_gives_short_tracks(tmp_path):
    path = _write_video(tmp_path / "klipp.mp4", 6)

    report = evaluate_detections(
        _run(tmp_path),
        video_frames(path, stride=1),
        detector_factory=lambda _run: _AlternatingDetector(),
        temporal=True,
    )

    assert report["stability"]["tracks"] == 3
    assert report["stability"]["mean_length"] == 1.0
    assert report["stability"]["stable_share"] == 0.0


def test_the_dataset_source_builds_the_map_report(tmp_path):
    dataset, images_dir = _write_dataset(tmp_path)

    report = evaluate_source(
        _run(tmp_path),
        EvaluationSource(kind=SOURCE_DATASET, split="all"),
        dataset,
        images_dir,
        detector_factory=lambda _run: _FakeDetector(
            {"1": [[2, 2, 12, 12]], "2": [[2, 2, 12, 12]]}
        ),
    )

    assert report["source"] == SOURCE_DATASET
    assert report["source_label"] == "Dataset (Alla)"
    assert report["overall"]["map50_95"] == 1.0


def test_a_folder_source_gives_detection_counts(tmp_path):
    _write_images(tmp_path / "bilder", 2)

    report = evaluate_source(
        _run(tmp_path),
        EvaluationSource(kind=SOURCE_FOLDER, path=tmp_path / "bilder"),
        detector_factory=lambda _run: _FakeDetector({"1": [[0, 0, 5, 5]]}),
    )

    assert report["source"] == SOURCE_FOLDER
    assert report["source_label"] == "Bildmapp: bilder"
    assert report["detections"]["total"] == 1


def test_a_dataset_source_without_a_dataset_is_an_error(tmp_path):
    with pytest.raises(ValueError):
        evaluate_source(
            _run(tmp_path), EvaluationSource(kind=SOURCE_DATASET, split="all")
        )


def test_compare_runs_evaluates_every_run_against_the_same_source(tmp_path):
    _write_images(tmp_path / "bilder", 2)
    runs = [_run(tmp_path, "forsta"), _run(tmp_path, "andra")]

    reports = compare_runs(
        runs,
        EvaluationSource(kind=SOURCE_FOLDER, path=tmp_path / "bilder"),
        detector_factory=lambda _run: _FakeDetector({"1": [[0, 0, 5, 5]]}),
    )

    assert [report["run_id"] for report in reports] == ["forsta", "andra"]


def test_the_summary_of_a_detection_report_names_the_counts(tmp_path):
    _write_images(tmp_path / "bilder", 2)
    report = evaluate_source(
        _run(tmp_path),
        EvaluationSource(kind=SOURCE_FOLDER, path=tmp_path / "bilder"),
        detector_factory=lambda _run: _FakeDetector({"1": [[0, 0, 5, 5]]}),
    )

    text = summary_text(report)

    assert "detektioner/bild" in text
    assert "med träff" in text
    assert "medelkonfidens" in text


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


def test_the_history_view_opens_the_comparison_dialog(qapp, tmp_path, monkeypatch):
    """Knappen öppnar dialogen med de markerade träningarna (TASK-158)."""
    from PySide6.QtCore import QObject, Qt, Signal

    from xray_detector.ui import training_history as history_module

    _history_run(tmp_path)
    view = history_module.TrainingHistoryView(
        tmp_path / "trained", _StubDataset(tmp_path / "images")
    )
    opened: list[list[str]] = []

    class _FakeDialog(QObject):
        finished = Signal(int)

        def __init__(self, runs, dataset, images_dir, parent=None) -> None:
            super().__init__(parent)
            opened.append([run.run_id for run in runs])

        def open(self) -> None:
            pass

    monkeypatch.setattr(history_module, "EvaluationDialog", _FakeDialog)
    view.table.item(0, history_module.CHECK_COLUMN).setCheckState(
        Qt.CheckState.Checked
    )

    view.evaluate_button.click()

    assert opened == [["korning"]]


def test_the_history_view_shows_the_saved_evaluation(qapp, tmp_path):
    from xray_detector.ui.training_history import TrainingHistoryView

    run = _history_run(tmp_path)
    save_evaluation(run, _fake_report(run))

    view = TrainingHistoryView(tmp_path / "trained")
    view.table.selectRow(0)

    assert "Utvärdering (all)" in view.evaluation_label.text()
    assert "mAP50-95 1.000" in view.evaluation_label.text()


def test_the_evaluate_button_needs_a_dataset(qapp, tmp_path):
    from PySide6.QtCore import Qt

    from xray_detector.ui.training_history import CHECK_COLUMN, TrainingHistoryView

    _history_run(tmp_path)
    view = TrainingHistoryView(tmp_path / "trained")
    view.table.item(0, CHECK_COLUMN).setCheckState(Qt.CheckState.Checked)

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
