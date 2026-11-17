"""Utvärdering av en tränad modell (TASK-95).

Det enda kvalitetstalet appen har är val-mAP från träningen, och det säger
inget om det som avgör om modellen går att driftsätta i en röntgenapp: hur ofta
den larmar på en bild utan farliga objekt, och om den håller på båda vyerna.
Modulen kör en vald tränad modell över en vald delmängd och sparar rapporten i
körningens katalog, så två körningar kan jämföras i efterhand.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np

from xray_detector.application.training_history import TrainingRun
from xray_detector.infrastructure.dataset_store.export import (
    SPLIT_RATIO,
    SPLIT_SEED,
    train_val_split,
    train_val_test_split,
)
from xray_detector.infrastructure.training.metrics import (
    TARGET_RECALL,
    Prediction,
    Target,
    false_alarms_per_image,
    mean_average_precision,
    recall_at,
    threshold_for_recall,
)

EVALUATION_NAME = "evaluation.json"
#: Delmängderna en körning kan utvärderas mot. "test" finns bara i RF-DETR:s
#: export; YOLO-exporten har train/val.
SPLIT_LABELS = {"test": "Test", "val": "Val", "all": "Alla"}
#: Låg tröskel så mAP räknas över hela precision/recall-kurvan.
EVAL_CONFIDENCE = 0.01


def default_split(family: str) -> str:
    """Den delmängd som är held-out för familjen."""
    return "test" if family == "rfdetr" else "val"


def available_splits(family: str) -> tuple[str, ...]:
    """Delmängderna som är held-out för familjen, plus hela datasetet."""
    return ("test", "val", "all") if family == "rfdetr" else ("val", "all")


def subset_images(
    dataset: dict,
    split: str,
    ratio: float = SPLIT_RATIO,
    seed: int = SPLIT_SEED,
) -> list[dict]:
    """Bilderna i den valda delmängden, med samma delning som exporten."""
    images = dataset["images"]
    if split == "all":
        return list(images)
    if split == "test":
        return train_val_test_split(images, ratio, seed)["test"]
    return train_val_split(images, ratio, seed)[1]


def view_labels(images: list[dict]) -> dict[int, str]:
    """Vy per bild ur bildens plats i fångstgruppen (TASK-95).

    Appen fångar två strömmar per fångstögonblick, så bilderna i samma grupp är
    samma scen sedd från var sitt håll. Platsen i gruppen är därför bildens vy,
    och en modell som faller på en vy syns bara när talen delas upp.
    """
    groups: dict[object, list[dict]] = {}
    for image in images:
        groups.setdefault(image.get("group") or image["id"], []).append(image)
    labels: dict[int, str] = {}
    for members in groups.values():
        for index, image in enumerate(sorted(members, key=lambda item: item["id"])):
            labels[image["id"]] = f"vy {index + 1}"
    return labels


def _class_index(dataset: dict) -> dict[str, int]:
    return {name: index for index, name in enumerate(dataset["classes"])}


def _prediction(detections, class_index: dict[str, int]) -> Prediction:
    boxes = []
    scores = []
    labels = []
    for detection in detections:
        index = class_index.get(detection.class_name)
        if index is None:
            continue
        boxes.append([detection.x1, detection.y1, detection.x2, detection.y2])
        scores.append(detection.confidence)
        labels.append(index)
    return Prediction(
        boxes=np.array(boxes, dtype=float).reshape(-1, 4),
        scores=np.array(scores, dtype=float),
        labels=np.array(labels, dtype=int),
    )


def _target(image: dict, class_index: dict[str, int]) -> Target:
    """Facit ur annoteringarna; bbox är (x, y, w, h) i pixlar."""
    boxes = []
    labels = []
    for annotation in image["annotations"]:
        index = class_index.get(annotation["class_name"])
        if index is None:
            continue
        x, y, width, height = annotation["bbox"]
        boxes.append([x, y, x + width, y + height])
        labels.append(index)
    return Target(
        boxes=np.array(boxes, dtype=float).reshape(-1, 4),
        labels=np.array(labels, dtype=int),
    )


def _default_detector(run: TrainingRun):
    from xray_detector.application.model_registry import ModelSpec, create_detector

    spec = ModelSpec(
        key=f"trained-{run.run_id}",
        label=run.run_id,
        family=run.family,
        weights=str(run.weights),
    )
    return create_detector(spec, EVAL_CONFIDENCE)


def evaluate_run(
    run: TrainingRun,
    dataset: dict,
    images_dir: Path,
    split: str | None = None,
    detector_factory=None,
    ratio: float = SPLIT_RATIO,
    seed: int = SPLIT_SEED,
) -> dict:
    """Kör modellen över en delmängd och räknar ut rapporten.

    Modellen laddas med den låga utvärderingströskeln, så mAP räknas över hela
    kurvan. Driftläget räknas fram efteråt ur samma förutsägelser: den tröskel
    som ger 95 % recall, och hur många falsklarm per bild den ger på de
    negativa bilderna.
    """
    split = split or default_split(run.family)
    images = subset_images(dataset, split, ratio, seed)
    class_index = _class_index(dataset)
    detector = (detector_factory or _default_detector)(run)
    views = view_labels(dataset["images"])

    predictions: list[Prediction] = []
    targets: list[Target] = []
    evaluated: list[dict] = []
    for image in images:
        frame = cv2.imread(str(Path(images_dir) / image["file_name"]))
        if frame is None:
            continue
        predictions.append(_prediction(detector.detect(frame), class_index))
        targets.append(_target(image, class_index))
        evaluated.append(image)

    positives = [index for index, image in enumerate(evaluated) if image["annotations"]]
    negatives = [index for index, image in enumerate(evaluated) if not image["annotations"]]

    report: dict = {
        "run_id": run.run_id,
        "family": run.family,
        "weights": str(run.weights),
        "split": split,
        "date": datetime.now(UTC).isoformat(),
        "images": len(evaluated),
        "positives": len(positives),
        "negatives": len(negatives),
        "overall": mean_average_precision(predictions, targets),
        "views": {},
    }
    for view in sorted(set(views.values())):
        index = [
            position
            for position, image in enumerate(evaluated)
            if views[image["id"]] == view
        ]
        if not index:
            continue
        report["views"][view] = {
            "images": len(index),
            **mean_average_precision(
                [predictions[position] for position in index],
                [targets[position] for position in index],
            ),
        }

    positive_predictions = [predictions[position] for position in positives]
    positive_targets = [targets[position] for position in positives]
    threshold = threshold_for_recall(positive_predictions, positive_targets)
    report["operating_point"] = {
        "target_recall": TARGET_RECALL,
        "threshold": threshold,
        "recall": (
            recall_at(positive_predictions, positive_targets, threshold)
            if positives
            else 0.0
        ),
    }
    negative_predictions = [predictions[position] for position in negatives]
    report["false_alarms"] = {
        "images": len(negatives),
        "total": sum(
            int((prediction.scores >= threshold).sum())
            for prediction in negative_predictions
        ),
        "per_image": false_alarms_per_image(negative_predictions, threshold),
    }
    return report


def save_evaluation(run: TrainingRun, report: dict) -> Path:
    """Sparar rapporten i körningens katalog, så två körningar kan jämföras."""
    path = Path(run.run_dir) / EVALUATION_NAME
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return path


def load_evaluation(run: TrainingRun) -> dict | None:
    """Körningens sparade utvärdering, eller None när den inte är utvärderad."""
    path = Path(run.run_dir) / EVALUATION_NAME
    try:
        with open(path, encoding="utf-8") as file:
            report = json.load(file)
    except (OSError, ValueError):
        return None
    return report if isinstance(report, dict) else None


def summary_text(report: dict) -> str:
    """Kort sammanfattning av en rapport för historikvyn."""
    overall = report.get("overall") or {}
    false_alarms = report.get("false_alarms") or {}
    operating = report.get("operating_point") or {}
    parts = [
        f"mAP50-95 {float(overall.get('map50_95') or 0.0):.3f}",
        f"mAP50 {float(overall.get('map50') or 0.0):.3f}",
    ]
    for view, values in sorted((report.get("views") or {}).items()):
        parts.append(f"{view} {float(values.get('map50_95') or 0.0):.3f}")
    parts.append(
        f"falsklarm/bild {float(false_alarms.get('per_image') or 0.0):.2f} "
        f"vid {float(operating.get('threshold') or 0.0):.2f} "
        f"({float(operating.get('target_recall') or 0.0):.0%} recall)"
    )
    return "  ·  ".join(parts)
