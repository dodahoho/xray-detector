import random
import shutil
from datetime import UTC, datetime
from pathlib import Path

from xray_detector.infrastructure.dataset_store.json_io import atomic_write_json
from xray_detector.infrastructure.dataset_store.store import DatasetStore

SPLIT_RATIO = 0.8
SPLIT_SEED = 42


def _category_map(coco: dict) -> dict[int, str]:
    return {category["id"]: category["name"] for category in coco["categories"]}


def train_val_split(coco: dict, ratio: float = SPLIT_RATIO, seed: int = SPLIT_SEED) -> tuple[list[dict], list[dict]]:
    """Delar upp bilderna i train/val gr-upperat på fångstgrupp.

    Bilder med samma "group"-id (samma fångstögonblick) hamnar alltid i
    samma delmängd så att vänster- och högerbild från samma scen inte läcker
    mellan train och val. Delningen är seedad och därmed reproducerbar.
    """
    groups: dict[object, list[dict]] = {}
    for image in coco["images"]:
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


def _fresh_dir(path: Path) -> Path:
    """Tömmer exportkatalogen så bilder från en tidigare export inte ligger kvar."""
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)
    return path


def export_yolo(store: DatasetStore, export_root: Path) -> Path:
    coco = store.load_coco()
    categories = _category_map(coco)
    class_names = [categories[cid] for cid in sorted(categories)]
    name_to_index = {name: index for index, name in enumerate(class_names)}

    out_dir = _fresh_dir(export_root / "yolo")
    source_images = store.images_dir
    train_images, val_images = train_val_split(coco)

    for split, images in (("train", train_images), ("val", val_images)):
        images_dir = out_dir / "images" / split
        labels_dir = out_dir / "labels" / split
        images_dir.mkdir(parents=True, exist_ok=True)
        labels_dir.mkdir(parents=True, exist_ok=True)
        for image in images:
            shutil.copy2(source_images / image["file_name"], images_dir / image["file_name"])
            label_path = labels_dir / (Path(image["file_name"]).stem + ".txt")
            lines = []
            for annotation in coco["annotations"]:
                if annotation["image_id"] != image["id"]:
                    continue
                x, y, w, h = annotation["bbox"]
                cx = x + w / 2
                cy = y + h / 2
                lines.append(
                    f"{name_to_index[categories[annotation['category_id']]]} "
                    f"{cx / image['width']:.6f} {cy / image['height']:.6f} "
                    f"{w / image['width']:.6f} {h / image['height']:.6f}"
                )
            label_path.write_text("\n".join(lines), encoding="utf-8")

    # Tom val-uppsättning (enda gruppen): låt val peka på train så att
    # ultralytics kan starta, men notera det i manifestet.
    val_relative = "images/val" if val_images else "images/train"

    data_yaml = out_dir / "data.yaml"
    data_yaml.write_text(
        "\n".join(
            [
                f"path: {out_dir}",
                "train: images/train",
                f"val: {val_relative}",
                f"nc: {len(class_names)}",
                f"names: {class_names}",
            ]
        ),
        encoding="utf-8",
    )
    write_manifest(out_dir, coco, "yolo",
                   num_train=len(train_images), num_val=len(val_images))
    return out_dir


def export_coco(store: DatasetStore, export_root: Path) -> Path:
    coco = store.load_coco()
    out_dir = _fresh_dir(export_root / "coco")
    (out_dir / "images").mkdir(parents=True, exist_ok=True)
    source_images = store.images_dir
    for image in coco["images"]:
        shutil.copy2(source_images / image["file_name"], out_dir / "images" / image["file_name"])
    atomic_write_json(out_dir / "dataset.json", coco)
    write_manifest(out_dir, coco, "coco")
    return out_dir


def write_manifest(out_dir: Path, coco: dict, export_format: str, **extra) -> None:
    manifest = {
        "format": export_format,
        "date": datetime.now(UTC).isoformat(),
        "num_images": len(coco["images"]),
        "num_objects": len(coco["annotations"]),
        **extra,
    }
    atomic_write_json(out_dir / "manifest.json", manifest)


def _coco_for_split(coco: dict, images: list[dict]) -> dict:
    """COCO-dokument för en delmängd bilder (RF-DETR:s per-split json)."""
    ids = {image["id"] for image in images}
    return {
        "info": dict(coco.get("info", {})),
        "licenses": coco.get("licenses", []),
        "categories": coco["categories"],
        "images": [dict(image) for image in images],
        "annotations": [
            dict(annotation) for annotation in coco["annotations"]
            if annotation["image_id"] in ids
        ],
    }


def export_rfdetr(store: DatasetStore, export_root: Path) -> Path:
    """Exporterar i RF-DETR:s forvantalade format: train/valid/test med _annotations.coco.json."""
    coco = store.load_coco()
    out_dir = _fresh_dir(export_root / "rfdetr")
    source_images = store.images_dir
    train, val = train_val_split(coco)

    for split, images in (("train", train), ("valid", val), ("test", val)):
        split_dir = out_dir / split
        (split_dir / "images").mkdir(parents=True, exist_ok=True)
        for image in images:
            shutil.copy2(
                source_images / image["file_name"],
                split_dir / "images" / image["file_name"],
            )
        split_coco = _coco_for_split(coco, images)
        for image in split_coco["images"]:
            image["file_name"] = f"images/{image['file_name']}"
        atomic_write_json(split_dir / "_annotations.coco.json", split_coco)

    write_manifest(out_dir, coco, "rfdetr",
                   num_train=len(train), num_val=len(val), num_test=len(val))
    return out_dir
