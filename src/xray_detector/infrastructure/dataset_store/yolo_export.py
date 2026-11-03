"""YOLO dataset export with pair-aware train/val splitting."""

from __future__ import annotations

import random
import shutil
from datetime import UTC, datetime
from pathlib import Path

import yaml

from xray_detector.infrastructure.dataset_store.coco_store import CocoStore, _atomic_write_json


def _split_pairs(
    coco: dict,
    train_split: float,
    val_split: float,
    seed: int,
) -> dict[str, set[str]]:
    pair_ids = sorted(
        {str(image.get("pair_id", f"image-{image['id']}")) for image in coco["images"]}
    )
    random.Random(seed).shuffle(pair_ids)

    total = len(pair_ids)
    train_count = int(round(total * train_split))
    val_count = int(round(total * val_split))
    if total > 1 and val_count == 0 and val_split > 0:
        val_count = 1
    train_count = min(train_count, max(0, total - val_count))
    val_count = min(val_count, total - train_count)

    train = set(pair_ids[:train_count])
    val = set(pair_ids[train_count : train_count + val_count])
    test = set(pair_ids[train_count + val_count :])
    return {"train": train, "val": val, "test": test}


def export_yolo(
    store: CocoStore,
    version: str,
    destination: Path,
    train_split: float = 0.8,
    val_split: float = 0.2,
    seed: int = 42,
) -> dict:
    """Export a frozen version to YOLO format and return the manifest."""
    coco = store.load_version(version)
    version_manifest = store.version_manifest(version)
    categories = sorted(coco.get("categories", []), key=lambda item: item["id"])
    category_index = {category["id"]: index for index, category in enumerate(categories)}
    class_names = [category["name"] for category in categories]

    splits = _split_pairs(coco, train_split, val_split, seed)
    annotations_by_image: dict[int, list[dict]] = {}
    for annotation in coco.get("annotations", []):
        annotations_by_image.setdefault(annotation["image_id"], []).append(annotation)

    destination.mkdir(parents=True, exist_ok=True)
    counts = {name: 0 for name in splits}
    annotation_counts = {name: 0 for name in splits}

    for split_name, pair_ids in splits.items():
        images_dir = destination / "images" / split_name
        labels_dir = destination / "labels" / split_name
        images_dir.mkdir(parents=True, exist_ok=True)
        labels_dir.mkdir(parents=True, exist_ok=True)

        for image in coco["images"]:
            pair_id = str(image.get("pair_id", f"image-{image['id']}"))
            if pair_id not in pair_ids:
                continue
            source = store.images_dir / image["file_name"]
            if not source.exists():
                continue
            shutil.copy2(source, images_dir / image["file_name"])
            counts[split_name] += 1

            width = image["width"]
            height = image["height"]
            lines = []
            for annotation in annotations_by_image.get(image["id"], []):
                class_index = category_index.get(annotation["category_id"])
                if class_index is None:
                    continue
                x, y, w, h = annotation["bbox"]
                if w <= 0 or h <= 0:
                    continue
                cx = (x + w / 2) / width
                cy = (y + h / 2) / height
                nw = w / width
                nh = h / height
                lines.append(f"{class_index} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")
                annotation_counts[split_name] += 1
            label_path = labels_dir / f"{Path(image['file_name']).stem}.txt"
            label_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    data = {
        "path": str(destination.resolve()),
        "train": "images/train",
        "val": "images/val",
        "names": {index: name for index, name in enumerate(class_names)},
    }
    if counts.get("test", 0) > 0:
        data["test"] = "images/test"
    with (destination / "data.yaml").open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False, allow_unicode=True)

    manifest = {
        "format": "yolo",
        "dataset": store.name,
        "version": version,
        "exported_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "image_count": version_manifest["image_count"],
        "pair_count": version_manifest["pair_count"],
        "annotation_count": version_manifest["annotation_count"],
        "category_counts": version_manifest["category_counts"],
        "source_created_at": version_manifest["created_at"],
        "splits": {
            name: {"images": counts[name], "annotations": annotation_counts[name]}
            for name in counts
        },
        "class_names": class_names,
    }
    _atomic_write_json(destination / "manifest.json", manifest)
    return manifest


__all__ = ["export_yolo"]
