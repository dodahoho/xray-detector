"""COCO export split into RF-DETR's expected train/valid/test layout."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

from xray_detector.infrastructure.dataset_store.coco_store import CocoStore, _atomic_write_json
from xray_detector.infrastructure.dataset_store.yolo_export import _split_pairs


def export_rfdetr(
    store: CocoStore,
    version: str,
    destination: Path,
    train_split: float = 0.8,
    val_split: float = 0.2,
    seed: int = 42,
) -> dict:
    coco = store.load_version(version)
    version_manifest = store.version_manifest(version)
    splits = _split_pairs(coco, train_split, val_split, seed)
    pair_to_split: dict[str, str] = {}
    for split_name, pair_ids in splits.items():
        for pair_id in pair_ids:
            pair_to_split[pair_id] = split_name

    categories = coco.get("categories", [])
    annotations_by_image: dict[int, list[dict]] = {}
    for annotation in coco.get("annotations", []):
        annotations_by_image.setdefault(annotation["image_id"], []).append(annotation)

    split_coco: dict[str, dict] = {}
    for split_name in ("train", "valid", "test"):
        split_dir = destination / split_name
        split_dir.mkdir(parents=True, exist_ok=True)
        split_coco[split_name] = {
            "info": {
                "description": f"{store.name} {version} {split_name}",
                "version": version,
                "date_created": datetime.now(UTC).replace(microsecond=0).isoformat(),
            },
            "licenses": [],
            "images": [],
            "annotations": [],
            "categories": categories,
        }

    for image in coco["images"]:
        pair_id = str(image.get("pair_id", f"image-{image['id']}"))
        split_name = pair_to_split.get(pair_id, "train")
        if split_name == "val":
            split_name = "valid"
        source = store.images_dir / image["file_name"]
        if not source.exists():
            continue
        target_dir = destination / split_name
        shutil.copy2(source, target_dir / image["file_name"])
        image_copy = dict(image)
        image_copy["file_name"] = image["file_name"]
        split_coco[split_name]["images"].append(image_copy)
        split_coco[split_name]["annotations"].extend(
            dict(annotation) for annotation in annotations_by_image.get(image["id"], [])
        )

    counts = {}
    for split_name, data in split_coco.items():
        _atomic_write_json(destination / split_name / "_annotations.coco.json", data)
        counts[split_name] = {
            "images": len(data["images"]),
            "annotations": len(data["annotations"]),
        }

    class_names = [category["name"] for category in sorted(categories, key=lambda item: item["id"])]
    manifest = {
        "format": "rfdetr-coco",
        "dataset": store.name,
        "version": version,
        "exported_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "image_count": version_manifest["image_count"],
        "pair_count": version_manifest["pair_count"],
        "annotation_count": version_manifest["annotation_count"],
        "category_counts": version_manifest["category_counts"],
        "source_created_at": version_manifest["created_at"],
        "splits": counts,
        "class_names": class_names,
    }
    _atomic_write_json(destination / "manifest.json", manifest)
    return manifest


__all__ = ["export_rfdetr"]
