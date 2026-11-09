import json
import random
import shutil
from datetime import UTC, datetime
from pathlib import Path

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


def export_yolo(store: DatasetStore, version: int, export_root: Path) -> Path:
    coco = store.load_coco(version)
    categories = _category_map(coco)
    class_names = [categories[cid] for cid in sorted(categories)]
    name_to_index = {name: index for index, name in enumerate(class_names)}

    out_dir = export_root / f"v{version}_yolo"
    source_images = store.version_dir(version) / "images"
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
    write_manifest(out_dir, coco, version, "yolo",
                   num_train=len(train_images), num_val=len(val_images))
    return out_dir


def export_coco(store: DatasetStore, version: int, export_root: Path) -> Path:
    coco = store.load_coco(version)
    out_dir = export_root / f"v{version}_coco"
    (out_dir / "images").mkdir(parents=True, exist_ok=True)
    source_images = store.version_dir(version) / "images"
    for image in coco["images"]:
        shutil.copy2(source_images / image["file_name"], out_dir / "images" / image["file_name"])
    with open(out_dir / "dataset.json", "w", encoding="utf-8") as file:
        json.dump(coco, file, ensure_ascii=False, indent=2)
    write_manifest(out_dir, coco, version, "coco")
    return out_dir


def write_manifest(out_dir: Path, coco: dict, version: int, export_format: str, **extra) -> None:
    manifest = {
        "version": version,
        "format": export_format,
        "date": datetime.now(UTC).isoformat(),
        "num_images": len(coco["images"]),
        "num_objects": len(coco["annotations"]),
        **extra,
    }
    with open(out_dir / "manifest.json", "w", encoding="utf-8") as file:
        json.dump(manifest, file, ensure_ascii=False, indent=2)
