"""Utvärdering av en tränad modell (TASK-95, TASK-158).

Det enda kvalitetstalet appen har är val-mAP från träningen, och det säger
inget om det som avgör om modellen går att driftsätta i en röntgenapp: hur ofta
den larmar på en bild utan farliga objekt, och om den håller på båda vyerna.
Modulen kör en vald tränad modell över en vald källa och sparar rapporten i
körningens katalog, så två körningar kan jämföras i efterhand.

Källan är antingen en delmängd av datasetet, som har annoteringar och därför
ger mAP och falsklarm, eller en mapp med bilder eller en videofil, som saknar
facit och där utvärderingen i stället räknar detektioner, konfidens och — för
en video — hur stabilt ett spår sitter mellan bildrutorna.
"""

import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np

from xray_detector.application import model_registry
from xray_detector.application.training_history import TrainingRun
from xray_detector.domain.dataset import group_images
from xray_detector.infrastructure.dataset_store.export import (
    SPLIT_RATIO,
    SPLIT_SEED,
    train_val_split,
    train_val_test_split,
)
from xray_detector.infrastructure.dataset_store.external import (
    IMAGE_SUFFIXES,
    read_dataset,
)
from xray_detector.infrastructure.training.metrics import (
    TARGET_RECALL,
    Prediction,
    Target,
    false_alarms_per_image,
    mean_average_precision,
    recall_at,
    stability_summary,
    threshold_for_recall,
    track_lengths,
)

EVALUATION_NAME = "evaluation.json"
#: Delmängderna en körning kan utvärderas mot. "test" finns bara i RF-DETR:s
#: export; YOLO-exporten har train/val.
SPLIT_LABELS = {"test": "Test", "val": "Val", "all": "Alla"}
#: Låg tröskel så mAP räknas över hela precision/recall-kurvan.
EVAL_CONFIDENCE = 0.01
#: Källtyperna utvärderingen kan köras mot (TASK-158).
SOURCE_DATASET = "dataset"
SOURCE_FOLDER = "folder"
SOURCE_VIDEO = "video"
SOURCE_LABELS = {
    SOURCE_DATASET: "Dataset",
    SOURCE_FOLDER: "Bildmapp",
    SOURCE_VIDEO: "Videofil",
}
#: Källor utan facit har ingen kurva att hitta driftläget ur, så de räknas vid
#: appens egen konfidenströskel: det antal detektioner användaren ser i
#: detektionsvyn.
DETECTION_CONFIDENCE = 0.4
#: Var stride:te bildruta läses ur en videofil; resten hoppas över.
VIDEO_STRIDE = 5
#: Antalet staplar i konfidenshistogrammet, över 0.0-1.0.
CONFIDENCE_BINS = 10


@dataclass(frozen=True)
class EvaluationSource:
    """Det utvärderingen körs mot: ett dataset, en mapp eller en video.

    path är satt när användaren pekar ut ett eget dataset i YOLO-format; utan
    path används applikationens eget dataset.
    """

    kind: str = SOURCE_DATASET
    split: str | None = None
    path: Path | None = None

    @property
    def label(self) -> str:
        """Källan som den visas i rapporten och i dialogens rubrik."""
        if self.kind == SOURCE_DATASET:
            split = self.split or ""
            name = SPLIT_LABELS.get(split, split)
            if self.path is not None:
                return f"Dataset ({name}): {Path(self.path).name}"
            return f"Dataset ({name})"
        name = Path(self.path).name if self.path else "-"
        return f"{SOURCE_LABELS.get(self.kind, self.kind)}: {name}"

    @property
    def temporal(self) -> bool:
        """Sant när bildrutorna kommer i tidsordning, alltså bara för en video."""
        return self.kind == SOURCE_VIDEO


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


def dataset_frames(
    dataset: dict,
    images_dir: Path,
    split: str,
    ratio: float = SPLIT_RATIO,
    seed: int = SPLIT_SEED,
) -> Iterator[tuple[str, np.ndarray, dict]]:
    """Bildrutorna i en delmängd av datasetet, med bildens annoteringar."""
    for image in subset_images(dataset, split, ratio, seed):
        frame = cv2.imread(str(Path(images_dir) / image["file_name"]))
        if frame is None:
            continue
        yield image["file_name"], frame, image


def folder_frames(folder: Path) -> Iterator[tuple[str, np.ndarray, None]]:
    """Bilderna i en mapp, sorterade på namn så ordningen blir densamma varje gång."""
    for path in sorted(Path(folder).iterdir()):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        frame = cv2.imread(str(path))
        if frame is None:
            continue
        yield path.name, frame, None


def video_frames(
    path: Path, stride: int = VIDEO_STRIDE
) -> Iterator[tuple[str, np.ndarray, None]]:
    """Bildrutor ur en videofil, var stride:te ruta.

    Var tionde ruta räcker för att jämföra modeller och håller nere tiden en
    utvärdering tar, samtidigt som rutsiffran blir tät nog för att ett spår
    ska synas över flera rutor.
    """
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError(f"Kunde inte öppna videofilen {path}")
    try:
        index = 0
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if index % stride == 0:
                yield f"ruta {index}", frame, None
            index += 1
    finally:
        capture.release()


def view_labels(images: list[dict]) -> dict[int, str]:
    """Vy per bild ur bildens plats i fångstgruppen (TASK-95).

    Appen fångar två strömmar per fångstögonblick, så bilderna i samma grupp är
    samma scen sedd från var sitt håll. Platsen i gruppen är därför bildens vy,
    och en modell som faller på en vy syns bara när talen delas upp.
    """
    labels: dict[int, str] = {}
    for members in group_images(images).values():
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
    spec = model_registry.ModelSpec(
        key=f"trained-{run.run_id}",
        label=run.run_id,
        family=run.family,
        weights=str(run.weights),
    )
    return model_registry.create_detector(spec, EVAL_CONFIDENCE)


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
    # Ett dataset utan fångstpar har bara en vy, och då säger uppdelningen
    # inget utöver helheten (TASK-158).
    if len(set(views.values())) > 1:
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


def _detection_class_index(detector) -> dict[str, int]:
    """Klassindex ur modellens egna namn; okända klasser läggs till efter hand."""
    return {
        str(name): index
        for index, name in enumerate(getattr(detector, "class_names", None) or [])
    }


def evaluate_detections(
    run: TrainingRun,
    frames: Iterator[tuple[str, np.ndarray, dict | None]],
    detector_factory=None,
    threshold: float = DETECTION_CONFIDENCE,
    temporal: bool = False,
) -> dict:
    """Räknar detektioner över bildrutor som saknar annoteringar (TASK-158).

    Utan facit går träffsäkerheten inte att mäta, så rapporten svarar i stället
    på hur mycket modellen larmar: detektioner per bild, per klass, hur stor
    andel av bilderna som får minst en träff och hur säkra träffarna är.
    temporal slår på stabiliteten, som kräver att bildrutorna kommer i
    tidsordning och därför bara räknas för en videofil.
    """
    detector = (detector_factory or _default_detector)(run)
    class_index = _detection_class_index(detector)
    predictions: list[Prediction] = []
    for _name, frame, _image in frames:
        detections = detector.detect(frame)
        for detection in detections:
            class_index.setdefault(detection.class_name, len(class_index))
        predictions.append(_prediction(detections, class_index))

    names = {index: name for name, index in class_index.items()}
    kept = [prediction.scores[prediction.scores >= threshold] for prediction in predictions]
    scores = np.concatenate(kept) if kept else np.zeros(0, dtype=float)
    histogram, _edges = np.histogram(scores, bins=CONFIDENCE_BINS, range=(0.0, 1.0))
    per_class: dict[str, int] = {}
    for prediction in predictions:
        for label in prediction.labels[prediction.scores >= threshold]:
            name = names.get(int(label), str(int(label)))
            per_class[name] = per_class.get(name, 0) + 1

    images = len(predictions)
    total = len(scores)
    report: dict = {
        "run_id": run.run_id,
        "family": run.family,
        "weights": str(run.weights),
        "date": datetime.now(UTC).isoformat(),
        "images": images,
        "threshold": threshold,
        "detections": {
            "total": total,
            "per_image": total / images if images else 0.0,
            "with_detection_share": (
                sum(1 for kept_scores in kept if len(kept_scores)) / images
                if images
                else 0.0
            ),
            "mean_confidence": float(scores.mean()) if total else 0.0,
            "histogram": [int(count) for count in histogram],
            "per_class": per_class,
        },
    }
    if temporal:
        report["stability"] = stability_summary(track_lengths(predictions))
    return report


def evaluate_source(
    run: TrainingRun,
    source: EvaluationSource,
    dataset: dict | None = None,
    images_dir: Path | None = None,
    detector_factory=None,
    ratio: float = SPLIT_RATIO,
    seed: int = SPLIT_SEED,
) -> dict:
    """Utvärderar en körning mot den valda källan (TASK-158).

    Datasetkällan har annoteringar och går till evaluate_run, som ger mAP och
    falsklarm. Pekar källan ut ett eget dataset på disk läses det i stället för
    appens eget. Mappen och videon saknar facit och går till
    evaluate_detections, som räknar detektioner i stället.
    """
    if source.kind == SOURCE_DATASET:
        if dataset is None and source.path is not None:
            dataset, images_dir = read_dataset(source.path)
        if dataset is None:
            raise ValueError("Dataset-utvärderingen kräver ett dataset")
        report = evaluate_run(
            run, dataset, images_dir, source.split, detector_factory, ratio, seed
        )
    else:
        if source.path is None:
            raise ValueError(f"{SOURCE_LABELS.get(source.kind, source.kind)} saknar sökväg")
        frames = (
            video_frames(source.path)
            if source.kind == SOURCE_VIDEO
            else folder_frames(source.path)
        )
        report = evaluate_detections(
            run, frames, detector_factory, temporal=source.temporal
        )
    report["source"] = source.kind
    report["source_label"] = source.label
    return report


def compare_runs(
    runs: list[TrainingRun],
    source: EvaluationSource,
    dataset: dict | None = None,
    images_dir: Path | None = None,
    detector_factory=None,
    ratio: float = SPLIT_RATIO,
    seed: int = SPLIT_SEED,
) -> list[dict]:
    """Utvärderar varje körning mot samma källa, så talen går att jämföra.

    Ett eget dataset på disk läses en gång och delas av alla körningarna, så
    bilderna bara behöver slås upp en gång per jämförelse.
    """
    if source.kind == SOURCE_DATASET and source.path is not None:
        dataset, images_dir = read_dataset(source.path)
    return [
        evaluate_source(run, source, dataset, images_dir, detector_factory, ratio, seed)
        for run in runs
    ]


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
    if report.get("source", SOURCE_DATASET) != SOURCE_DATASET:
        return detection_summary_text(report)
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


def detection_summary_text(report: dict) -> str:
    """Sammanfattning av en rapport för en källa utan annoteringar (TASK-158)."""
    detections = report.get("detections") or {}
    parts = [
        f"detektioner/bild {float(detections.get('per_image') or 0.0):.2f}",
        f"{float(detections.get('with_detection_share') or 0.0):.0%} av bilderna med träff",
        f"medelkonfidens {float(detections.get('mean_confidence') or 0.0):.2f}",
    ]
    stability = report.get("stability")
    if stability:
        parts.append(
            f"spår {int(stability.get('tracks') or 0)} st, "
            f"medellängd {float(stability.get('mean_length') or 0.0):.1f} rutor"
        )
    return "  ·  ".join(parts)
