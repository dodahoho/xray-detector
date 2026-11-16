"""mAP och falsklarm för en tränad detektor (TASK-95).

Beräkningarna är rena funktioner på numpy-arrayer, så de går att testa utan
GPU, torch eller en modell. Modulen känner inte till YOLO eller RF-DETR: den
får förutsägelser och facit per bild och räknar ut samma tal som
utvärderingsrapporten visar.
"""

from dataclasses import dataclass

import numpy as np

#: IoU-trösklarna i COCO:s mAP50-95.
IOU_THRESHOLDS = tuple(round(0.5 + 0.05 * index, 2) for index in range(10))
#: Matchningströskeln för recall och falsklarm.
MATCH_IOU = 0.5
#: Recall-nivån som driftläget räknas fram för.
TARGET_RECALL = 0.95
#: Konfidenströsklarna som driftläget söks igenom.
CONFIDENCE_STEPS = tuple(round(0.01 + 0.01 * index, 2) for index in range(99))


@dataclass(frozen=True)
class Prediction:
    """En bilds förutsägelser: rutor i xyxy, konfidenser och klassindex."""

    boxes: np.ndarray
    scores: np.ndarray
    labels: np.ndarray

    @classmethod
    def empty(cls) -> "Prediction":
        return cls(
            boxes=np.zeros((0, 4), dtype=float),
            scores=np.zeros(0, dtype=float),
            labels=np.zeros(0, dtype=int),
        )


@dataclass(frozen=True)
class Target:
    """En bilds facit: rutor i xyxy och klassindex."""

    boxes: np.ndarray
    labels: np.ndarray

    @classmethod
    def empty(cls) -> "Target":
        return cls(boxes=np.zeros((0, 4), dtype=float), labels=np.zeros(0, dtype=int))


def iou_matrix(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    """IoU mellan varje ruta i first och varje ruta i second."""
    first = np.asarray(first, dtype=float).reshape(-1, 4)
    second = np.asarray(second, dtype=float).reshape(-1, 4)
    if len(first) == 0 or len(second) == 0:
        return np.zeros((len(first), len(second)), dtype=float)
    left_top = np.maximum(first[:, None, :2], second[None, :, :2])
    right_bottom = np.minimum(first[:, None, 2:], second[None, :, 2:])
    overlap = np.clip(right_bottom - left_top, 0, None)
    intersection = overlap[..., 0] * overlap[..., 1]
    first_area = np.clip(first[:, 2] - first[:, 0], 0, None) * np.clip(
        first[:, 3] - first[:, 1], 0, None
    )
    second_area = np.clip(second[:, 2] - second[:, 0], 0, None) * np.clip(
        second[:, 3] - second[:, 1], 0, None
    )
    union = first_area[:, None] + second_area[None, :] - intersection
    return np.where(union > 0, intersection / union, 0.0)


def match_counts(
    prediction: Prediction,
    target: Target,
    threshold: float,
    iou_threshold: float = MATCH_IOU,
) -> tuple[int, int, int]:
    """Girig matchning per klass vid en konfidenströskel: (tp, fp, fn)."""
    keep = prediction.scores >= threshold
    boxes = prediction.boxes[keep]
    labels = prediction.labels[keep]
    matched = np.zeros(len(target.boxes), dtype=bool)
    true_positives = 0
    for class_id in np.unique(labels):
        predicted = np.where(labels == class_id)[0]
        truth = np.where(target.labels == class_id)[0]
        if len(truth) == 0:
            continue
        overlaps = iou_matrix(boxes[predicted], target.boxes[truth])
        for row in range(overlaps.shape[0]):
            best_column = -1
            best_overlap = iou_threshold
            for column in range(overlaps.shape[1]):
                if matched[truth[column]]:
                    continue
                if overlaps[row, column] >= best_overlap:
                    best_column = column
                    best_overlap = overlaps[row, column]
            if best_column >= 0:
                matched[truth[best_column]] = True
                true_positives += 1
    false_positives = int(keep.sum()) - true_positives
    false_negatives = len(target.labels) - true_positives
    return true_positives, false_positives, false_negatives


def recall_at(predictions: list[Prediction], targets: list[Target], threshold: float) -> float:
    """Andel hittade objekt vid en konfidenströskel."""
    true_positives = 0
    false_negatives = 0
    for prediction, target in zip(predictions, targets, strict=False):
        found, _, missed = match_counts(prediction, target, threshold)
        true_positives += found
        false_negatives += missed
    total = true_positives + false_negatives
    return true_positives / total if total else 0.0


def threshold_for_recall(
    predictions: list[Prediction],
    targets: list[Target],
    target_recall: float = TARGET_RECALL,
) -> float:
    """Lägsta konfidenströskel som fortfarande når target_recall."""
    for threshold in CONFIDENCE_STEPS:
        if recall_at(predictions, targets, threshold) >= target_recall:
            return threshold
    return CONFIDENCE_STEPS[0]


def false_alarms_per_image(predictions: list[Prediction], threshold: float) -> float:
    """Antal larm per bild vid en konfidenströskel."""
    if not predictions:
        return 0.0
    total = sum(int((prediction.scores >= threshold).sum()) for prediction in predictions)
    return total / len(predictions)


def _class_ap(
    predictions: list[Prediction],
    targets: list[Target],
    class_id: int,
    iou_threshold: float,
) -> float | None:
    """AP för en klass vid en IoU-tröskel; None när klassen saknas i facit."""
    truth_by_image = [target.boxes[target.labels == class_id] for target in targets]
    positives = sum(len(boxes) for boxes in truth_by_image)
    if positives == 0:
        return None
    entries = [
        (float(score), image_index, box)
        for image_index, prediction in enumerate(predictions)
        for box, score in zip(
            prediction.boxes[prediction.labels == class_id],
            prediction.scores[prediction.labels == class_id],
            strict=False,
        )
    ]
    entries.sort(key=lambda entry: -entry[0])
    matched = [np.zeros(len(boxes), dtype=bool) for boxes in truth_by_image]
    true_positives = 0
    false_positives = 0
    average_precision = 0.0
    previous_recall = 0.0
    for _score, image_index, box in entries:
        truth = truth_by_image[image_index]
        if len(truth) == 0:
            false_positives += 1
        else:
            overlaps = iou_matrix(box[None, :], truth)[0]
            overlaps = np.where(matched[image_index], -1.0, overlaps)
            best = int(np.argmax(overlaps))
            if overlaps[best] >= iou_threshold:
                matched[image_index][best] = True
                true_positives += 1
            else:
                false_positives += 1
        precision = true_positives / (true_positives + false_positives)
        recall = true_positives / positives
        average_precision += (recall - previous_recall) * precision
        previous_recall = recall
    return average_precision


def mean_average_precision(
    predictions: list[Prediction], targets: list[Target]
) -> dict[str, float]:
    """mAP50-95 och mAP50 över alla klasser som finns i facit."""
    classes = sorted({int(label) for target in targets for label in target.labels})
    if not classes:
        return {"map50_95": 0.0, "map50": 0.0}
    per_threshold = []
    for iou_threshold in IOU_THRESHOLDS:
        scores = [
            score
            for score in (
                _class_ap(predictions, targets, class_id, iou_threshold)
                for class_id in classes
            )
            if score is not None
        ]
        per_threshold.append(float(np.mean(scores)) if scores else 0.0)
    return {
        "map50_95": float(np.mean(per_threshold)),
        "map50": per_threshold[0],
    }
