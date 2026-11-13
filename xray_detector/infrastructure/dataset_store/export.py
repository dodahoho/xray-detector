import random
import shutil
from datetime import UTC, datetime
from pathlib import Path

from xray_detector.infrastructure.dataset_store.json_io import atomic_write_json
from xray_detector.infrastructure.dataset_store.store import DatasetStore
from xray_detector.infrastructure.dataset_store.yolo import label_name, write_data_yaml

SPLIT_RATIO = 0.8
SPLIT_SEED = 42


def train_val_split(
    images: list[dict],
    ratio: float = SPLIT_RATIO,
    seed: int = SPLIT_SEED,
) -> tuple[list[dict], list[dict]]:
    """Delar upp bilderna i train/val grupperat på fångstgrupp.

    Bilder med samma "group"-id (samma fångstögonblick) hamnar alltid i
    samma delmängd så att vänster- och högerbild från samma scen inte läcker
    mellan train och val. Delningen är seedad och därmed reproducerbar.
    """
    groups: dict[object, list[dict]] = {}
    for image in images:
        key = image.get("group") or image["id"]
        groups.setdefault(key, []).append(image)
    keys = sorted(groups, key=str)
    random.Random(seed).shuffle(keys)
    cutoff = int(round(len(keys) * ratio))
    if keys and cutoff == 0:
        cutoff = 1
    train: list[dict] = []
    val: list[dict] = []
    for index, key in enumerate(keys):
        (train if index < cutoff else val).extend(groups[key])
    return train, val


def group_count(images: list[dict]) -> int:
    """Antal fångstgrupper (bildpar) i en lista bilder (TASK-72)."""
    return len({image.get("group") or image["id"] for image in images})


def _fresh_dir(path: Path) -> Path:
    """Tömmer exportkatalogen så bilder från en tidigare export inte ligger kvar."""
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)
    return path


def export_yolo(store: DatasetStore, export_root: Path, ratio: float = SPLIT_RATIO) -> Path:
    """Kopierar datasetet som ett YOLO-dataset med train/val-delning.

    Datasetet lagras redan i YOLO-format, så exporten kopierar bilder och
    label-filer och skriver en data.yaml för delningen (TASK-78).
    """
    dataset = store.load_dataset()
    out_dir = _fresh_dir(export_root / "yolo")
    train_images, val_images = train_val_split(dataset["images"], ratio)

    for split, images in (("train", train_images), ("val", val_images)):
        images_dir = out_dir / "images" / split
        labels_dir = out_dir / "labels" / split
        images_dir.mkdir(parents=True, exist_ok=True)
        labels_dir.mkdir(parents=True, exist_ok=True)
        for image in images:
            shutil.copy2(
                store.images_dir / image["file_name"],
                images_dir / image["file_name"],
            )
            name = label_name(image["file_name"])
            source = store.labels_dir / name
            if source.exists():
                shutil.copy2(source, labels_dir / name)
            else:
                # YOLO kräver en label-fil även för negativa exempel
                (labels_dir / name).write_text("", encoding="utf-8")

    # Tom val-uppsättning (enda gruppen): låt val peka på train så att
    # ultralytics kan starta, men notera det i manifestet.
    val_relative = "images/val" if val_images else "images/train"
    write_data_yaml(
        out_dir / "data.yaml", dataset["classes"], "images/train", val_relative
    )
    write_manifest(
        out_dir,
        dataset,
        "yolo",
        num_train=len(train_images),
        num_val=len(val_images),
    )
    return out_dir


def export_coco(store: DatasetStore, export_root: Path) -> Path:
    """Exporterar datasetet som ett COCO-dataset för verktyg som kräver det."""
    dataset = store.load_dataset()
    out_dir = _fresh_dir(export_root / "coco")
    (out_dir / "images").mkdir(parents=True, exist_ok=True)
    for image in dataset["images"]:
        shutil.copy2(
            store.images_dir / image["file_name"],
            out_dir / "images" / image["file_name"],
        )
    atomic_write_json(out_dir / "dataset.json", _coco_document(dataset, dataset["images"]))
    write_manifest(out_dir, dataset, "coco")
    return out_dir


def write_manifest(out_dir: Path, dataset: dict, export_format: str, **extra) -> None:
    manifest = {
        "format": export_format,
        "date": datetime.now(UTC).isoformat(),
        "num_images": len(dataset["images"]),
        "num_objects": sum(len(image["annotations"]) for image in dataset["images"]),
        **extra,
    }
    atomic_write_json(out_dir / "manifest.json", manifest)


def _coco_document(dataset: dict, images: list[dict]) -> dict:
    """COCO-dokument för en delmängd bilder (export till COCO och RF-DETR).

    YOLO:s klassindex blir COCO:s category_id med ett tillagt ett, eftersom
    COCO numrerar kategorierna från 1.
    """
    names = dataset["classes"]
    category_of = {name: index + 1 for index, name in enumerate(names)}
    coco_images = []
    annotations = []
    annotation_id = 1
    for image in images:
        coco_images.append(
            {
                "id": image["id"],
                "file_name": image["file_name"],
                "width": image["width"],
                "height": image["height"],
            }
        )
        for annotation in image["annotations"]:
            category_id = category_of.get(annotation["class_name"])
            if category_id is None:
                continue
            annotations.append(
                {
                    "id": annotation_id,
                    "image_id": image["id"],
                    "category_id": category_id,
                    "bbox": [round(value, 2) for value in annotation["bbox"]],
                }
            )
            annotation_id += 1
    return {
        "info": dict(dataset["info"]),
        "licenses": [],
        "categories": [
            {"id": index + 1, "name": name} for index, name in enumerate(names)
        ],
        "images": coco_images,
        "annotations": annotations,
    }


def export_rfdetr(store: DatasetStore, export_root: Path, ratio: float = SPLIT_RATIO) -> Path:
    """Exporterar i RF-DETR:s forvantalade format: train/valid/test med _annotations.coco.json."""
    dataset = store.load_dataset()
    out_dir = _fresh_dir(export_root / "rfdetr")
    train, val = train_val_split(dataset["images"], ratio)

    for split, images in (("train", train), ("valid", val), ("test", val)):
        split_dir = out_dir / split
        (split_dir / "images").mkdir(parents=True, exist_ok=True)
        for image in images:
            shutil.copy2(
                store.images_dir / image["file_name"],
                split_dir / "images" / image["file_name"],
            )
        split_coco = _coco_document(dataset, images)
        for image in split_coco["images"]:
            image["file_name"] = f"images/{image['file_name']}"
        atomic_write_json(split_dir / "_annotations.coco.json", split_coco)

    write_manifest(
        out_dir,
        dataset,
        "rfdetr",
        num_train=len(train),
        num_val=len(val),
        num_test=len(val),
    )
    return out_dir
